import os
import json
import hmac
import time
import hashlib
import secrets
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from urllib.parse import urlparse, parse_qs

from db import get_connection


HOST = "localhost"
PORT = 8000


# =========================================================
# FRONTEND DIRECTORY
# =========================================================

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
FRONTEND_DIR = os.path.join(BASE_DIR, "..", "frontend")

os.chdir(FRONTEND_DIR)


# =========================================================
# SESSIONS (login tokens)
# =========================================================
# After a successful login the server creates a random token and
# sends it to the browser. The browser sends it back in the
# "Authorization: Bearer <token>" header on every protected request.
# The server then knows WHO is calling - the user id in the URL is
# never trusted.
#
# Sessions are kept in memory, so they are cleared when the server
# restarts (users just have to log in again).

SESSION_TTL = 8 * 60 * 60          # a session lasts 8 hours
SESSIONS = {}                      # token -> {"user_id", "role", "expires"}


def create_session(user_id, role):
    token = secrets.token_urlsafe(32)
    SESSIONS[token] = {
        "user_id": user_id,
        "role": role,
        "expires": time.time() + SESSION_TTL
    }
    return token


def get_session(token):
    session = SESSIONS.get(token)
    if not session:
        return None
    if session["expires"] < time.time():
        SESSIONS.pop(token, None)
        return None
    return session


# =========================================================
# PASSWORD HASHING (standard library only)
# =========================================================
# Format stored in the database:
#   pbkdf2_sha256$<iterations>$<salt>$<hash>      (about 120 characters)
# The password / confirm_password columns must be at least
# VARCHAR(255). Old plain-text passwords still work once and are
# converted to a hash automatically at that user's next login.

PBKDF2_ITERATIONS = 200000
HASH_PREFIX = "pbkdf2_sha256$"


def hash_password(password):
    salt = secrets.token_hex(16)
    digest = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt),
        PBKDF2_ITERATIONS
    ).hex()
    return "{}{}${}${}".format(
        HASH_PREFIX, PBKDF2_ITERATIONS, salt, digest
    )


def is_hashed(stored):
    return bool(stored) and str(stored).startswith(HASH_PREFIX)


def verify_password(password, stored):
    if not stored:
        return False
    stored = str(stored)

    # Old accounts created before hashing was added
    if not is_hashed(stored):
        return hmac.compare_digest(
            password.encode("utf-8"),
            stored.encode("utf-8")
        )

    try:
        _, iterations, salt, digest = stored.split("$")
        check = hashlib.pbkdf2_hmac(
            "sha256",
            password.encode("utf-8"),
            bytes.fromhex(salt),
            int(iterations)
        ).hex()
        return hmac.compare_digest(check, digest)
    except Exception:
        return False


# =========================================================
# SERVER CLASS
# =========================================================

class FoodDonationServer(SimpleHTTPRequestHandler):


    # =====================================================
    # SEND JSON RESPONSE
    # =====================================================

    def send_json(self, data, status=200):

        response = json.dumps(
            data,
            default=str
        ).encode("utf-8")

        self.send_response(status)

        self.send_header(
            "Content-Type",
            "application/json"
        )

        self.send_header(
            "Content-Length",
            str(len(response))
        )

        self.send_header(
            "Access-Control-Allow-Origin",
            "*"
        )

        self.end_headers()

        self.wfile.write(response)


    # =====================================================
    # AUTHENTICATION HELPERS
    # =====================================================

    def current_user(self):
        auth = self.headers.get("Authorization", "")
        if not auth.startswith("Bearer "):
            return None
        return get_session(auth[7:].strip())


    def require_role(self, role):
        """Return the logged-in user, or send 401/403 and return None."""

        user = self.current_user()

        if not user:
            self.send_json({
                "success": False,
                "message": "Please log in again."
            }, 401)
            return None

        if user["role"] != role:
            self.send_json({
                "success": False,
                "message": "Access denied."
            }, 403)
            return None

        return user


    # =====================================================
    # GET REQUESTS
    # =====================================================

    def do_GET(self):

        # All /api/donor/... GET routes need a logged-in donor.
        # The donor id comes from the session, NOT from the URL.
        user = None

        if self.path.startswith("/api/donor/"):
            user = self.require_role("donor")
            if not user:
                return

        if self.path.startswith("/api/receiver/"):
            user = self.require_role("receiver")
            if not user:
                return


        # =================================================
        # RECEIVER DASHBOARD
        # =================================================

        if self.path.startswith("/api/receiver/dashboard"):
            conn = None
            cursor = None
            try:
                receiver_id = user["user_id"]
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)

                cursor.execute("""
                    SELECT organization_name
                    FROM ngos
                    WHERE ngo_id = %s
                """, (receiver_id,))
                receiver = cursor.fetchone()

                if not receiver:
                    self.send_json({
                        "success": False,
                        "message": "Receiver not found"
                    }, 404)
                    return

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM donation
                    WHERE LOWER(status) = 'pending'
                """)
                available = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM donation
                    WHERE ngo_id = %s
                      AND LOWER(status) IN ('accepted', 'approved')
                """, (receiver_id,))
                accepted = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM pickup_request
                    WHERE ngo_id = %s
                      AND pickup_time IS NOT NULL
                      AND DATE(pickup_time) = CURDATE()
                      AND LOWER(status) IN ('accepted', 'approved')
                """, (receiver_id,))
                today_pickups = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM donation
                    WHERE ngo_id = %s
                      AND LOWER(status) IN ('picked up', 'collected', 'completed')
                """, (receiver_id,))
                completed = cursor.fetchone()["total"]

                cursor.execute("""
                    SELECT
                        d.donation_id,
                        d.food_name,
                        d.food_category,
                        d.quantity,
                        d.status,
                        d.created_at,
                        donor.resturaent_name AS restaurant,
                        donor.city
                    FROM donation AS d
                    JOIN donor ON donor.donor_id = d.donor_id
                    WHERE LOWER(d.status) = 'pending'
                    ORDER BY d.created_at DESC
                    LIMIT 5
                """)
                donations = cursor.fetchall()

                self.send_json({
                    "success": True,
                    "receiver": receiver,
                    "stats": {
                        "available": available,
                        "accepted": accepted,
                        "today_pickups": today_pickups,
                        "completed": completed
                    },
                    "donations": donations
                })
            except Exception as e:
                print("RECEIVER DASHBOARD ERROR:", e)
                self.send_json({
                    "success": False,
                    "message": str(e)
                }, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return



        # =================================================
        # DONOR DASHBOARD
        # =================================================

        if self.path.startswith("/api/donor/dashboard"):

            try:

                parsed_url = urlparse(self.path)

                query = parse_qs(
                    parsed_url.query
                )

                donor_id = user["user_id"]


                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )


                # =========================================
                # GET DONOR
                # =========================================

                cursor.execute("""
                    SELECT
                        donor_id,
                        resturaent_name
                    FROM donor
                    WHERE donor_id = %s
                """, (donor_id,))


                donor = cursor.fetchone()


                if not donor:

                    cursor.close()
                    conn.close()

                    self.send_json({
                        "success": False,
                        "message": "Donor not found"
                    }, 404)

                    return


                # =========================================
                # TOTAL DONATIONS
                # =========================================

                cursor.execute("""
                    SELECT COUNT(*) AS total
                    FROM donation
                    WHERE donor_id = %s
                """, (donor_id,))


                total = cursor.fetchone()["total"]


                # =========================================
                # TODAY'S DONATIONS
                # =========================================

                cursor.execute("""
                    SELECT COUNT(*) AS today
                    FROM donation
                    WHERE donor_id = %s
                    AND DATE(created_at) = CURDATE()
                """, (donor_id,))


                today = cursor.fetchone()["today"]


                # =========================================
                # ACCEPTED DONATIONS
                # =========================================

                cursor.execute("""
                    SELECT COUNT(*) AS accepted
                    FROM donation
                    WHERE donor_id = %s
                    AND LOWER(status) = 'accepted'
                """, (donor_id,))


                accepted = cursor.fetchone()["accepted"]


                # =========================================
                # PENDING DONATIONS
                # =========================================

                cursor.execute("""
                    SELECT COUNT(*) AS pending
                    FROM donation
                    WHERE donor_id = %s
                    AND LOWER(status) = 'pending'
                """, (donor_id,))


                pending = cursor.fetchone()["pending"]


                # =========================================
                # LATEST DONATIONS
                # =========================================

                cursor.execute("""
                    SELECT
                        donation_id,
                        food_name,
                        quantity,
                        description,
                        pickup_time,
                        status,
                        created_at
                    FROM donation
                    WHERE donor_id = %s
                    ORDER BY created_at DESC
                    LIMIT 5
                """, (donor_id,))


                donations = cursor.fetchall()


                # =========================================
                # CLOSE DATABASE
                # =========================================

                cursor.close()
                conn.close()


                # =========================================
                # SEND DASHBOARD DATA
                # =========================================

                self.send_json({

                    "success": True,

                    "donor": donor,

                    "stats": {

                        "total": total,

                        "today": today,

                        "accepted": accepted,

                        "pending": pending

                    },

                    "donations": donations

                })


            except Exception as e:

                print(
                    "DONOR DASHBOARD ERROR:",
                    e
                )

                self.send_json({

                    "success": False,

                    "message": str(e)

                }, 500)

            return


        # =================================================
        # DONOR PROFILE
        # =================================================

        if self.path.startswith("/api/donor/profile"):

            try:

                parsed_url = urlparse(
                    self.path
                )

                query = parse_qs(
                    parsed_url.query
                )

                donor_id = user["user_id"]


                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )


                cursor.execute("""
                    SELECT
                        donor_id,
                        resturaent_name,
                        owner_name,
                        email,
                        phone,
                        address,
                        city,
                        location,
                        created_at
                    FROM donor
                    WHERE donor_id = %s
                """, (donor_id,))


                donor = cursor.fetchone()


                cursor.close()
                conn.close()


                if donor:

                    self.send_json({

                        "success": True,

                        "donor": donor

                    })

                else:

                    self.send_json({

                        "success": False,

                        "message": "Donor not found"

                    }, 404)


            except Exception as e:

                print(
                    "DONOR PROFILE ERROR:",
                    e
                )

                self.send_json({

                    "success": False,

                    "message": str(e)

                }, 500)

            return


        # =================================================
        # DONOR DONATION HISTORY
        # =================================================

        if self.path.startswith("/api/donor/donations"):

            try:

                parsed_url = urlparse(
                    self.path
                )

                query = parse_qs(
                    parsed_url.query
                )

                donor_id = user["user_id"]

                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )

                cursor.execute("""
                    SELECT
                        donation_id,
                        donor_id,
                        food_name,
                        food_category,
                        quantity,
                        cooking_date,
                        expiry_time,
                        contact_number,
                        description,
                        food_image,
                        pickup_time,
                        status,
                        created_at
                    FROM donation
                    WHERE donor_id = %s
                    ORDER BY created_at DESC
                """, (donor_id,))

                donations = cursor.fetchall()

                cursor.close()
                conn.close()

                self.send_json({
                    "success": True,
                    "donations": donations
                })

            except Exception as e:

                print(
                    "DONATION HISTORY ERROR:",
                    e
                )

                self.send_json({
                    "success": False,
                    "message": str(e)
                }, 500)

            return

        # =================================================
        # NORMAL HTML / FILE REQUEST
        # =================================================

        return super().do_GET()


    # =====================================================
    # POST REQUESTS
    # =====================================================

    def do_POST(self):


        # =================================================
        # READ REQUEST DATA
        # =================================================

        try:

            content_length = int(
                self.headers.get(
                    "Content-Length",
                    0
                )
            )


            if content_length == 0:

                self.send_json({

                    "success": False,

                    "message":
                        "Request body is empty"

                }, 400)

                return


            body = self.rfile.read(
                content_length
            )


            if not body:

                self.send_json({

                    "success": False,

                    "message":
                        "Request body is empty"

                }, 400)

                return


            data = json.loads(
                body.decode("utf-8")
            )


            if not isinstance(data, dict):

                self.send_json({

                    "success": False,

                    "message":
                        "Invalid JSON data"

                }, 400)

                return


        except json.JSONDecodeError as e:

            self.send_json({

                "success": False,

                "message":
                    "Invalid JSON request: " + str(e)

            }, 400)

            return


        except Exception as e:

            self.send_json({

                "success": False,

                "message":
                    "Invalid request data: " + str(e)

            }, 400)

            return


        # =================================================
        # LOGOUT
        # =================================================

        if self.path == "/api/logout":

            auth = self.headers.get("Authorization", "")

            if auth.startswith("Bearer "):
                SESSIONS.pop(auth[7:].strip(), None)

            self.send_json({
                "success": True,
                "message": "Logged out"
            })

            return


        # =================================================
        # DONOR FOOD DONATION
        # =================================================

        if self.path == "/api/donor/donate":

            try:

                user = self.require_role("donor")

                if not user:
                    return


                required_fields = [
                    "food_name",
                    "food_category",
                    "quantity",
                    "cooking_date",
                    "expiry_time"
                ]

                for field in required_fields:

                    if not data.get(field):

                        self.send_json({
                            "success": False,
                            "message":
                                field.replace("_", " ").title()
                                + " is required"
                        }, 400)

                        return

                donor_id = user["user_id"]

                food_name = str(
                    data["food_name"]
                ).strip()

                food_category = str(
                    data["food_category"]
                ).strip()

                quantity = str(
                    data["quantity"]
                ).strip()

                cooking_date = str(
                    data["cooking_date"]
                ).strip()

                expiry_time = str(
                    data["expiry_time"]
                ).strip()

                contact_number = str(
                    data.get("contact_number", "")
                ).strip()

                description = str(
                    data.get("description", "")
                ).strip()

                food_image = str(
                    data.get("food_image", "")
                )

                # CHECK DONOR ID

                if not donor_id.startswith("DN"):

                    self.send_json({
                        "success": False,
                        "message": "Invalid donor ID"
                    }, 400)

                    return

                # CONNECT DATABASE

                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )

                # CHECK DONOR EXISTS

                cursor.execute("""
                    SELECT
                        donor_id,
                        resturaent_name,
                        owner_name,
                        phone,
                        address,
                        city
                    FROM donor
                    WHERE donor_id = %s
                """, (donor_id,))

                donor = cursor.fetchone()

                if not donor:

                    cursor.close()
                    conn.close()

                    self.send_json({
                        "success": False,
                        "message": "Donor not found"
                    }, 404)

                    return

                # The form has no contact field - use the donor's own phone
                if not contact_number:
                    contact_number = str(donor.get("phone") or "")

                # INSERT DONATION

                cursor.execute("""
                    INSERT INTO donation
                    (
                        donor_id,
                        food_name,
                        food_category,
                        quantity,
                        cooking_date,
                        expiry_time,
                        contact_number,
                        description,
                        food_image,
                        pickup_time,
                        status
                    )
                    VALUES
                    (
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s, %s
                    )
                """, (
                    donor_id,
                    food_name,
                    food_category,
                    quantity,
                    cooking_date,
                    expiry_time,
                    contact_number,
                    description,
                    food_image,
                    None,
                    "Pending"
                ))

                donation_id = cursor.lastrowid

                conn.commit()

                cursor.close()
                conn.close()

                self.send_json({
                    "success": True,
                    "message":
                        "Food donation submitted successfully",
                    "donation_id":
                        donation_id
                })

            except Exception as e:

                print(
                    "FOOD DONATION ERROR:",
                    e
                )

                self.send_json({
                    "success": False,
                    "message": str(e)
                }, 500)

            return


        # =================================================
        # DONOR REGISTRATION
        # =================================================

        if self.path == "/api/donor/register":

            try:

                required_fields = [

                    "restaurant_name",
                    "owner_name",
                    "email",
                    "phone",
                    "address",
                    "city",
                    "password",
                    "confirm_password",
                    "location"

                ]


                for field in required_fields:

                    if not data.get(field):

                        self.send_json({

                            "success": False,

                            "message":
                                field.replace(
                                    "_",
                                    " "
                                ).title()
                                + " is required"

                        }, 400)

                        return


                # =========================================
                # PASSWORD CHECK
                # =========================================

                if (
                    data["password"]
                    != data["confirm_password"]
                ):

                    self.send_json({

                        "success": False,

                        "message":
                            "Passwords do not match"

                    }, 400)

                    return


                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )


                # =========================================
                # CHECK EMAIL
                # =========================================

                cursor.execute("""
                    SELECT donor_id
                    FROM donor
                    WHERE email = %s
                """, (data["email"],))


                existing = cursor.fetchone()


                if existing:

                    cursor.close()
                    conn.close()

                    self.send_json({

                        "success": False,

                        "message":
                            "Email already registered"

                    }, 400)

                    return


                # =========================================
                # GENERATE DONOR ID
                # =========================================

                cursor.execute("""
                    SELECT donor_id
                    FROM donor
                    ORDER BY donor_id DESC
                    LIMIT 1
                """)


                last_donor = cursor.fetchone()


                if last_donor:

                    try:

                        last_number = int(
                            last_donor["donor_id"][2:]
                        )

                    except:

                        last_number = 0

                else:

                    last_number = 0


                donor_id = "DN{:03d}".format(
                    last_number + 1
                )


                # =========================================
                # INSERT DONOR
                # =========================================

                cursor.execute("""
                    INSERT INTO donor
                    (
                        donor_id,
                        resturaent_name,
                        owner_name,
                        email,
                        phone,
                        address,
                        city,
                        password,
                        confirm_password,
                        location
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (

                    donor_id,

                    data["restaurant_name"],

                    data["owner_name"],

                    data["email"],

                    data["phone"],

                    data["address"],

                    data["city"],

                    hash_password(data["password"]),
                    "",

                    data["location"]

                ))


                conn.commit()


                cursor.close()
                conn.close()


                self.send_json({

                    "success": True,

                    "message":
                        "Donor registration successful",

                    "donor_id":
                        donor_id

                })


            except Exception as e:

                print(
                    "DONOR REGISTRATION ERROR:",
                    e
                )

                self.send_json({

                    "success": False,

                    "message": str(e)

                }, 500)

            return


        # =================================================
        # RECEIVER REGISTRATION
        # =================================================

        elif self.path == "/api/receiver/register":

            try:

                required_fields = [

                    "organization_name",
                    "organization_type",
                    "representative_name",
                    "email",
                    "phone",
                    "address",
                    "city",
                    "password",
                    "confirm_password",
                    "location"

                ]


                for field in required_fields:

                    if not data.get(field):

                        self.send_json({

                            "success": False,

                            "message":
                                field.replace(
                                    "_",
                                    " "
                                ).title()
                                + " is required"

                        }, 400)

                        return


                # =========================================
                # PASSWORD CHECK
                # =========================================

                if (
                    data["password"]
                    != data["confirm_password"]
                ):

                    self.send_json({

                        "success": False,

                        "message":
                            "Passwords do not match"

                    }, 400)

                    return


                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )


                # =========================================
                # CHECK EMAIL
                # =========================================

                cursor.execute("""
                    SELECT ngo_id
                    FROM ngos
                    WHERE email = %s
                """, (data["email"],))


                existing = cursor.fetchone()


                if existing:

                    cursor.close()
                    conn.close()

                    self.send_json({

                        "success": False,

                        "message":
                            "Email already registered"

                    }, 400)

                    return


                # =========================================
                # GENERATE RECEIVER ID
                # =========================================

                cursor.execute("""
                    SELECT ngo_id
                    FROM ngos
                    ORDER BY ngo_id DESC
                    LIMIT 1
                """)


                last_ngo = cursor.fetchone()


                if last_ngo:

                    try:

                        last_number = int(
                            last_ngo["ngo_id"][2:]
                        )

                    except:

                        last_number = 0

                else:

                    last_number = 0


                ngo_id = "RN{:03d}".format(
                    last_number + 1
                )


                # =========================================
                # INSERT RECEIVER
                # =========================================

                cursor.execute("""
                    INSERT INTO ngos
                    (
                        ngo_id,
                        organization_name,
                        organization_type,
                        representative_name,
                        email,
                        phone,
                        address,
                        city,
                        password,
                        confirm_password,
                        location
                    )
                    VALUES
                    (
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s,
                        %s
                    )
                """, (

                    ngo_id,

                    data["organization_name"],

                    data["organization_type"],

                    data["representative_name"],

                    data["email"],

                    data["phone"],

                    data["address"],

                    data["city"],

                    hash_password(data["password"]),
                    "",

                    data["location"]

                ))


                conn.commit()


                cursor.close()
                conn.close()


                self.send_json({

                    "success": True,

                    "message":
                        "Receiver registration successful",

                    "ngo_id":
                        ngo_id

                })


            except Exception as e:

                print(
                    "RECEIVER REGISTRATION ERROR:",
                    e
                )

                self.send_json({

                    "success": False,

                    "message": str(e)

                }, 500)

            return


        # =================================================
        # LOGIN
        # =================================================

               # =================================================
        # LOGIN
        # =================================================

        if self.path == "/api/login":

            try:

                # =========================================
                # GET LOGIN DATA
                # =========================================

                userid = str(
                    data.get("userid", "")
                ).strip().upper()

                username = str(
                    data.get("username", "")
                ).strip()

                password = str(
                    data.get("password", "")
                )

                email = str(
                    data.get("email", "")
                ).strip()


                # =========================================
                # CHECK EMPTY FIELDS
                # =========================================

                if not userid:

                    self.send_json({
                        "success": False,
                        "message": "Please enter User ID."
                    }, 400)

                    return


                if not username:

                    self.send_json({
                        "success": False,
                        "message": "Please enter User Name."
                    }, 400)

                    return


                if not password:

                    self.send_json({
                        "success": False,
                        "message": "Please enter Password."
                    }, 400)

                    return


                if not email:

                    self.send_json({
                        "success": False,
                        "message": "Please enter Email ID."
                    }, 400)

                    return


                # =========================================
                # DATABASE CONNECTION
                # =========================================

                conn = get_connection()

                cursor = conn.cursor(
                    dictionary=True
                )


                # =========================================
                # DONOR LOGIN
                # =========================================

                if userid.startswith("DN"):

                    cursor.execute("""
                        SELECT
                            donor_id,
                            owner_name,
                            email,
                            resturaent_name,
                            password
                        FROM donor
                        WHERE donor_id = %s
                        AND owner_name = %s
                        AND email = %s
                    """, (
                        userid,
                        username,
                        email
                    ))


                    user = cursor.fetchone()

                    stored_password = (
                        user.pop("password", None) if user else None
                    )

                    if user and verify_password(password, stored_password):

                        # Upgrade old plain-text passwords to a hash
                        if not is_hashed(stored_password):
                            cursor.execute(
                                "UPDATE donor SET password = %s, confirm_password = %s WHERE donor_id = %s",
                                (hash_password(password), "", user["donor_id"])
                            )
                            conn.commit()

                        token = create_session(user["donor_id"], "donor")

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": True,

                            "message":
                                "Login successful",

                            "role": "donor",
                            "token": token,

                            "user_id":
                                user["donor_id"],

                            "user":
                                user

                        })


                        return


                    else:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": False,

                            "message":
                                "Donor details do not match. Please check User ID, User Name, Password and Email."

                        }, 401)


                        return


                # =========================================
                # RECEIVER / NGO LOGIN
                # =========================================

                elif userid.startswith("RN"):

                    cursor.execute("""
                        SELECT
                            ngo_id,
                            representative_name,
                            email,
                            organization_name,
                            password
                        FROM ngos
                        WHERE ngo_id = %s
                        AND representative_name = %s
                        AND email = %s
                    """, (
                        userid,
                        username,
                        email
                    ))


                    user = cursor.fetchone()

                    stored_password = (
                        user.pop("password", None) if user else None
                    )

                    if user and verify_password(password, stored_password):

                        # Upgrade old plain-text passwords to a hash
                        if not is_hashed(stored_password):
                            cursor.execute(
                                "UPDATE ngos SET password = %s, confirm_password = %s WHERE ngo_id = %s",
                                (hash_password(password), "", user["ngo_id"])
                            )
                            conn.commit()

                        token = create_session(user["ngo_id"], "receiver")

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": True,

                            "message":
                                "Login successful",

                            "role": "receiver",
                            "token": token,

                            "user_id":
                                user["ngo_id"],

                            "user":
                                user

                        })


                        return


                    else:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": False,

                            "message":
                                "Receiver details do not match. Please check User ID, User Name, Password and Email."

                        }, 401)


                        return


                # =========================================
                # INVALID USER ID
                # =========================================

                else:

                    cursor.close()
                    conn.close()


                    self.send_json({

                        "success": False,

                        "message":
                            "Invalid User ID. Use DN001 for Donor or RN001 for Receiver."

                    }, 400)


                    return


            except Exception as e:

                print(
                    "LOGIN ERROR:",
                    e
                )


                self.send_json({

                    "success": False,

                    "message":
                        "Login error: " + str(e)

                }, 500)


            return


        # =================================================
        # UNKNOWN API
        # =================================================

        self.send_json({
        
        "success": False,
        
        "message": "API endpoint not found"
        
        }, 404)


# =========================================================
# START SERVER
# =========================================================

if __name__ == "__main__":

    server = ThreadingHTTPServer(
        (HOST, PORT),
        FoodDonationServer
    )


    print(
        "HungerFree server running at:"
    )


    print(
        "http://localhost:8000"
    )


    print(
        "Press CTRL+C to stop the server."
    )


    try:

        server.serve_forever()

    except KeyboardInterrupt:

        print(
            "\nServer stopped."
        )

        server.server_close()
