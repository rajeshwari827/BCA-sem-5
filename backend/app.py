import os
import json
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from db import get_connection

HOST = "localhost"
PORT = 8000

# Serve files from the frontend folder
FRONTEND_DIR = os.path.join(
    os.path.dirname(__file__),
    "..",
    "frontend"
)

os.chdir(FRONTEND_DIR)


class FoodDonationServer(SimpleHTTPRequestHandler):

    def do_POST(self):

        print("POST Request Received")
        print("Path:", self.path)

        # ============================
        # LOGIN API
        # ============================
        if self.path == "/api/login":

            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            print("Received Data:", data)

            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            user_id = data["userid"]
            password = data["password"]

            if user_id.startswith("DN"):

                cursor.execute(
                    "SELECT * FROM donor WHERE donor_id=%s AND password=%s",
                    (user_id, password)
                )

            elif user_id.startswith("RN"):

                cursor.execute(
                    "SELECT * FROM ngos WHERE ngo_id=%s AND password=%s",
                    (user_id, password)
                )

            else:

                self.send_response(400)
                self.send_header("Content-Type", "application/json")
                self.end_headers()

                self.wfile.write(json.dumps({
                    "success": False,
                    "message": "Invalid User ID"
                }).encode())

                return

            user = cursor.fetchone()

            cursor.close()
            conn.close()

            if user:
                response = {
                    "success": True,
                    "message": "Login Successful"
                }
            else:
                response = {
                    "success": False,
                    "message": "Invalid User ID or Password"
                }

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(json.dumps(response).encode())

        # ============================
        # DONOR REGISTRATION API
        # ============================
        elif self.path == "/api/donor/register":

            content_length = int(self.headers["Content-Length"])
            body = self.rfile.read(content_length)
            data = json.loads(body)

            conn = get_connection()
            cursor = conn.cursor(dictionary=True)

            # Generate Donor ID
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

            # Insert Donor
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
                (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s)
            """,
            (
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

            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()

            self.wfile.write(json.dumps({
                "success": True,
                "message": "Registration Successful",
                "donor_id": donor_id
            }).encode())

        # ============================
        # INVALID API
        # ============================
        else:
            self.send_error(404, "API Not Found")


print(f"Serving frontend from: {FRONTEND_DIR}")
print(f"Server running at http://{HOST}:{PORT}")

server = ThreadingHTTPServer((HOST, PORT), FoodDonationServer)
server.serve_forever()