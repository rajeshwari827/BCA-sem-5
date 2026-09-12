import os
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from db import get_connection

HOST = "localhost"
PORT = 8000

# Frontend folder
FRONTEND_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "frontend"
)

os.chdir(FRONTEND_DIR)


class FoodDonationServer(SimpleHTTPRequestHandler):

    # =========================================
    # SEND JSON RESPONSE
    # =========================================

    def send_json(self, data, status=200):

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()

        self.wfile.write(
            json.dumps(data).encode()
        )

    # =========================================
    # POST REQUEST
    # =========================================

    def do_POST(self):

        print("\nPOST Request Received")
        print("Path:", self.path)

        # =====================================
        # DONOR REGISTRATION
        # =====================================

        if self.path == "/api/donor/register":

            try:

                content_length = int(
                    self.headers.get("Content-Length", 0)
                )

                body = self.rfile.read(content_length)

                data = json.loads(body)

                print("Donor Data Received:")
                print(data)

                # -----------------------------
                # Validate required fields
                # -----------------------------

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
                            "message": f"{field} is required"
                        }, 400)

                        return

                # -----------------------------
                # Check password
                # -----------------------------

                if data["password"] != data["confirm_password"]:

                    self.send_json({
                        "success": False,
                        "message": "Passwords do not match"
                    }, 400)

                    return

                # -----------------------------
                # Database connection
                # -----------------------------

                conn = get_connection()

                cursor = conn.cursor(dictionary=True)

                # -----------------------------
                # Generate Donor ID
                # -----------------------------

                cursor.execute("""
                    SELECT donor_id
                    FROM donor
                    ORDER BY donor_id DESC
                    LIMIT 1
                """)

                last = cursor.fetchone()

                if last is None:

                    donor_id = "DN001"

                else:

                    number = int(last["donor_id"][2:])

                    donor_id = f"DN{number + 1:03d}"

                # -----------------------------
                # Insert donor
                # -----------------------------

                query = """
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
                        %s, %s, %s, %s, %s,
                        %s, %s, %s, %s, %s
                    )
                """

                values = (
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
                )

                cursor.execute(query, values)

                conn.commit()

                cursor.close()
                conn.close()

                print("Donor Registered Successfully:", donor_id)

                # -----------------------------
                # Send success response
                # -----------------------------

                self.send_json({
                    "success": True,
                    "message": "Donor Registration Successful",
                    "donor_id": donor_id
                })

            except Exception as e:

                print("DATABASE ERROR:", e)

                self.send_json({
                    "success": False,
                    "message": "Database error: " + str(e)
                }, 500)

            return

        # =====================================
        # LOGIN
        # =====================================

        elif self.path == "/api/login":

            try:

                content_length = int(
                    self.headers.get("Content-Length", 0)
                )

                body = self.rfile.read(content_length)

                data = json.loads(body)

                user_id = data.get("userid")
                password = data.get("password")

                conn = get_connection()

                cursor = conn.cursor(dictionary=True)

                # -----------------------------
                # DONOR LOGIN
                # -----------------------------

                if user_id.startswith("DN"):

                    cursor.execute(
                        """
                        SELECT *
                        FROM donor
                        WHERE donor_id = %s
                        AND password = %s
                        """,
                        (user_id, password)
                    )

                # -----------------------------
                # NGO LOGIN
                # -----------------------------

                elif user_id.startswith("RN"):

                    cursor.execute(
                        """
                        SELECT *
                        FROM ngos
                        WHERE ngo_id = %s
                        AND password = %s
                        """,
                        (user_id, password)
                    )

                else:

                    cursor.close()
                    conn.close()

                    self.send_json({
                        "success": False,
                        "message": "Invalid User ID"
                    }, 400)

                    return

                user = cursor.fetchone()

                cursor.close()
                conn.close()

                if user:

                    self.send_json({
                        "success": True,
                        "message": "Login Successful"
                    })

                else:

                    self.send_json({
                        "success": False,
                        "message": "Invalid User ID or Password"
                    }, 401)

            except Exception as e:

                print("LOGIN ERROR:", e)

                self.send_json({
                    "success": False,
                    "message": str(e)
                }, 500)

            return

        # =====================================
        # INVALID API
        # =====================================

        else:

            self.send_error(
                404,
                "API Not Found"
            )


print("---------------------------------------")
print("HungerFree Food Donation System")
print("---------------------------------------")
print("Frontend:", FRONTEND_DIR)
print("Server: http://localhost:8000")
print("---------------------------------------")

server = ThreadingHTTPServer(
    (HOST, PORT),
    FoodDonationServer
)

server.serve_forever()