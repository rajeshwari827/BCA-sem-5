import os
import json
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
    # GET REQUESTS
    # =====================================================

    def do_GET(self):


        # =================================================
        # DONOR DASHBOARD
        # =================================================

        if self.path.startswith("/api/donor/dashboard"):

            try:

                parsed_url = urlparse(self.path)

                query = parse_qs(
                    parsed_url.query
                )

                donor_id = query.get(
                    "donor_id",
                    [None]
                )[0]


                if not donor_id:

                    self.send_json({
                        "success": False,
                        "message": "Donor ID is required"
                    }, 400)

                    return


                donor_id = donor_id.strip().upper()


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

                donor_id = query.get(
                    "donor_id",
                    [None]
                )[0]


                if not donor_id:

                    self.send_json({
                        "success": False,
                        "message": "Donor ID is required"
                    }, 400)

                    return


                donor_id = donor_id.strip().upper()


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

                donor_id = query.get(
                    "donor_id",
                    [None]
                )[0]

                if not donor_id:

                    self.send_json({
                        "success": False,
                        "message": "Donor ID is required"
                    }, 400)

                    return

                donor_id = donor_id.strip().upper()

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
        # DONOR FOOD DONATION
        # =================================================

        if self.path == "/api/donor/donate":

            try:

                required_fields = [
                    "donor_id",
                    "food_name",
                    "food_category",
                    "quantity",
                    "cooking_date",
                    "expiry_time",
                    "contact_number"
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

                donor_id = str(
                    data["donor_id"]
                ).strip().upper()

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
                    data["contact_number"]
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

                    data["password"],

                    data["confirm_password"],

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

                    data["password"],

                    data["confirm_password"],

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
                            resturaent_name
                        FROM donor
                        WHERE donor_id = %s
                        AND owner_name = %s
                        AND email = %s
                        AND password = %s
                    """, (
                        userid,
                        username,
                        email,
                        password
                    ))


                    user = cursor.fetchone()


                    if user:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": True,

                            "message":
                                "Login successful",

                            "role":
                                "donor",

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
                            organization_name
                        FROM ngos
                        WHERE ngo_id = %s
                        AND representative_name = %s
                        AND email = %s
                        AND password = %s
                    """, (
                        userid,
                        username,
                        email,
                        password
                    ))


                    user = cursor.fetchone()


                    if user:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": True,

                            "message":
                                "Login successful",

                            "role":
                                "receiver",

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
