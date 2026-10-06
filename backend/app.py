import os
import json
import hmac
import time
import hashlib
import secrets
import io
import zipfile
from html import escape
from http.server import ThreadingHTTPServer, SimpleHTTPRequestHandler
from http.cookies import SimpleCookie
from urllib.parse import urlparse, parse_qs

from db import get_connection
from util.email_notifications import send_acceptance_emails


HOST = "localhost"
PORT = 8000


def build_report_pdf(lines):
    """Build a small one-page PDF using the built-in Helvetica font."""
    commands = ["BT", "/F1 12 Tf", "50 760 Td"]
    for index, line in enumerate(lines):
        safe_line = str(line).encode("ascii", "replace").decode("ascii")
        safe_line = safe_line.replace("\\", "\\\\").replace("(", "\\(").replace(")", "\\)")
        if index:
            commands.append("0 -22 Td")
        commands.append("({}) Tj".format(safe_line))
    commands.append("ET")
    stream = "\n".join(commands).encode("ascii")
    objects = [
        b"<< /Type /Catalog /Pages 2 0 R >>",
        b"<< /Type /Pages /Kids [3 0 R] /Count 1 >>",
        b"<< /Type /Page /Parent 2 0 R /MediaBox [0 0 612 792] /Resources << /Font << /F1 4 0 R >> >> /Contents 5 0 R >>",
        b"<< /Type /Font /Subtype /Type1 /BaseFont /Helvetica >>",
        "<< /Length {} >>\nstream\n".format(len(stream)).encode("ascii") + stream + b"\nendstream"
    ]
    output = bytearray(b"%PDF-1.4\n")
    offsets = [0]
    for number, obj in enumerate(objects, 1):
        offsets.append(len(output))
        output.extend("{} 0 obj\n".format(number).encode("ascii"))
        output.extend(obj)
        output.extend(b"\nendobj\n")
    xref_offset = len(output)
    output.extend("xref\n0 {}\n".format(len(objects) + 1).encode("ascii"))
    output.extend(b"0000000000 65535 f \n")
    for offset in offsets[1:]:
        output.extend("{:010d} 00000 n \n".format(offset).encode("ascii"))
    output.extend("trailer\n<< /Size {} /Root 1 0 R >>\nstartxref\n{}\n%%EOF".format(len(objects) + 1, xref_offset).encode("ascii"))
    return bytes(output)


def build_report_xlsx(rows):
    """Create a minimal valid .xlsx workbook without third-party packages."""
    worksheet_rows = []
    for row_index, values in enumerate(rows, 1):
        cells = []
        for column_index, value in enumerate(values, 1):
            column = ""
            current = column_index
            while current:
                current, remainder = divmod(current - 1, 26)
                column = chr(65 + remainder) + column
            reference = "{}{}".format(column, row_index)
            text_value = "" if value is None else str(value)
            if text_value.isdigit():
                cells.append('<c r="{}"><v>{}</v></c>'.format(reference, text_value))
            else:
                cells.append('<c r="{}" t="inlineStr"><is><t xml:space="preserve">{}</t></is></c>'.format(
                    reference, escape(text_value)
                ))
        worksheet_rows.append('<row r="{}">{}</row>'.format(row_index, "".join(cells)))
    sheet = ('<?xml version="1.0" encoding="UTF-8" standalone="yes"?>'
             '<worksheet xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main">'
             '<sheetData>{}</sheetData></worksheet>').format("".join(worksheet_rows))

    buffer = io.BytesIO()
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as workbook:
        workbook.writestr("[Content_Types].xml", '''<?xml version="1.0" encoding="UTF-8"?>
<Types xmlns="http://schemas.openxmlformats.org/package/2006/content-types">
<Default Extension="rels" ContentType="application/vnd.openxmlformats-package.relationships+xml"/>
<Default Extension="xml" ContentType="application/xml"/>
<Override PartName="/xl/workbook.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml"/>
<Override PartName="/xl/worksheets/sheet1.xml" ContentType="application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml"/>
</Types>''')
        workbook.writestr("_rels/.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument" Target="xl/workbook.xml"/>
</Relationships>''')
        workbook.writestr("xl/workbook.xml", '''<?xml version="1.0" encoding="UTF-8"?>
<workbook xmlns="http://schemas.openxmlformats.org/spreadsheetml/2006/main" xmlns:r="http://schemas.openxmlformats.org/officeDocument/2006/relationships">
<sheets><sheet name="Reports" sheetId="1" r:id="rId1"/></sheets>
</workbook>''')
        workbook.writestr("xl/_rels/workbook.xml.rels", '''<?xml version="1.0" encoding="UTF-8"?>
<Relationships xmlns="http://schemas.openxmlformats.org/package/2006/relationships">
<Relationship Id="rId1" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet" Target="worksheets/sheet1.xml"/>
</Relationships>''')
        workbook.writestr("xl/worksheets/sheet1.xml", sheet)
    return buffer.getvalue()


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

    def send_json(self, data, status=200, extra_headers=None):

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

        for name, value in (extra_headers or {}).items():
            self.send_header(name, value)

        self.end_headers()

        self.wfile.write(response)


    def send_download(self, content, content_type, filename):
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(content)))
        self.send_header("Content-Disposition", 'attachment; filename="{}"'.format(filename))
        self.send_header("Cache-Control", "no-store")
        self.end_headers()
        self.wfile.write(content)


    # =====================================================
    # AUTHENTICATION HELPERS
    # =====================================================

    def current_user(self):
        auth = self.headers.get("Authorization", "")
        if auth.startswith("Bearer "):
            session = get_session(auth[7:].strip())
            if session:
                return session

        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        admin_cookie = cookies.get("admin_session")
        if admin_cookie:
            session = get_session(admin_cookie.value)
            if session and session.get("role") == "admin":
                return session
        return None


    def expire_admin_cookie(self):
        cookies = SimpleCookie(self.headers.get("Cookie", ""))
        admin_cookie = cookies.get("admin_session")
        if admin_cookie:
            SESSIONS.pop(admin_cookie.value, None)
        return {
            "Set-Cookie": "admin_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"
        }


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

        request_path = urlparse(self.path).path
        if request_path == "/admin_logout":
            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            admin_cookie = cookies.get("admin_session")
            if admin_cookie:
                SESSIONS.pop(admin_cookie.value, None)
            self.send_response(302)
            self.send_header("Location", "/login.html")
            self.send_header(
                "Set-Cookie",
                "admin_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"
            )
            self.end_headers()
            return

        if request_path == "/admin" or request_path.startswith("/admin/"):
            user = self.current_user()
            if not user or user.get("role") != "admin":
                self.send_response(302)
                self.send_header("Location", "/login.html")
                self.end_headers()
                return

        if request_path.startswith("/api/admin/"):
            admin_user = self.require_role("admin")
            if not admin_user:
                return

            if request_path == "/api/admin/dashboard":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)

                    cursor.execute("SELECT COUNT(*) AS total FROM donor")
                    total_donors = cursor.fetchone()["total"]

                    cursor.execute("SELECT COUNT(*) AS total FROM ngos")
                    total_ngos = cursor.fetchone()["total"]

                    cursor.execute("SELECT COUNT(*) AS total FROM donation")
                    total_donations = cursor.fetchone()["total"]

                    cursor.execute("""
                        SELECT COUNT(*) AS total
                        FROM donation
                        WHERE LOWER(status) = 'pending'
                    """)
                    pending_donations = cursor.fetchone()["total"]

                    cursor.execute("""
                        SELECT COUNT(*) AS total
                        FROM donation
                        WHERE LOWER(status) IN ('completed', 'collected', 'picked up')
                    """)
                    completed_donations = cursor.fetchone()["total"]

                    # Recent activity is supplementary. A schema mismatch in
                    # this query must not hide successfully fetched totals.
                    activities = []
                    try:
                        cursor.execute("""
                            SELECT d.created_at AS date,
                                   CONCAT('Donation #', d.donation_id, ' — ',
                                          COALESCE(d.food_name, 'Food donation'),
                                          ' by ', COALESCE(donor.resturaent_name, 'a donor')) AS activity,
                                   d.status AS status
                            FROM donation AS d
                            LEFT JOIN donor ON donor.donor_id = d.donor_id
                            ORDER BY d.created_at DESC
                            LIMIT 8
                        """)
                        activities = cursor.fetchall()
                    except Exception as activity_error:
                        print("ADMIN DASHBOARD ACTIVITY QUERY ERROR:", activity_error)

                    # Admin schemas may call the display-name field either
                    # username or admin_name. Keep that optional lookup from
                    # preventing the dashboard totals from loading.
                    admin_name = "Admin"
                    try:
                        cursor.execute("SHOW COLUMNS FROM admin")
                        admin_columns = {column["Field"] for column in cursor.fetchall()}
                        name_column = next(
                            (name for name in ("username", "admin_name", "user_name")
                             if name in admin_columns),
                            None
                        )
                        if name_column:
                            cursor.execute(
                                "SELECT `{}` AS admin_name FROM admin WHERE admin_id = %s LIMIT 1".format(name_column),
                                (admin_user["user_id"],)
                            )
                            admin = cursor.fetchone()
                            if admin and admin.get("admin_name"):
                                admin_name = admin["admin_name"]
                    except Exception as name_error:
                        print("ADMIN DASHBOARD NAME LOOKUP ERROR:", name_error)

                    self.send_json({
                        "success": True,
                        "admin_name": admin_name,
                        "total_users": total_donors + total_ngos,
                        "total_donors": total_donors,
                        "total_receivers": total_ngos,
                        "total_ngos": total_ngos,
                        "total_donations": total_donations,
                        "pending_donations": pending_donations,
                        "completed_donations": completed_donations,
                        "activities": activities
                    })
                except Exception as e:
                    print("ADMIN DASHBOARD ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load admin dashboard data."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/users":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT donor_id AS user_id,
                               owner_name AS name,
                               email,
                               phone,
                               city,
                               'Donor' AS role,
                               COALESCE(NULLIF(status, ''), 'Active') AS status
                        FROM donor
                        UNION ALL
                        SELECT ngo_id AS user_id,
                               representative_name AS name,
                               email,
                               phone,
                               city,
                               'NGO' AS role,
                               COALESCE(NULLIF(status, ''), 'Active') AS status
                        FROM ngos
                        ORDER BY user_id
                    """)
                    users = cursor.fetchall()
                    self.send_json({"success": True, "users": users})
                except Exception as e:
                    print("ADMIN USERS ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load registered users."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/donors":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT donor_id,
                               resturaent_name AS restaurant_name,
                               owner_name,
                               email,
                               phone,
                               city,
                               COALESCE(NULLIF(status, ''), 'Active') AS status
                        FROM donor
                        ORDER BY donor_id
                    """)
                    donors = cursor.fetchall()
                    self.send_json({"success": True, "donors": donors})
                except Exception as e:
                    print("ADMIN DONORS ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load registered donors."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/ngos":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT ngo_id,
                               organization_name AS ngo_name,
                               representative_name AS representative,
                               email,
                               phone,
                               city,
                               COALESCE(NULLIF(status, ''), 'Active') AS status
                        FROM ngos
                        ORDER BY ngo_id
                    """)
                    ngos = cursor.fetchall()
                    self.send_json({"success": True, "ngos": ngos})
                except Exception as e:
                    print("ADMIN NGOS ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load registered NGOs."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/donations":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT d.donation_id,
                               COALESCE(donor.owner_name, donor.resturaent_name, 'Unknown donor') AS donor,
                               d.food_name,
                               d.food_category AS category,
                               d.quantity,
                               COALESCE(donor.city, '') AS city,
                               d.created_at AS date,
                               d.status
                        FROM donation AS d
                        LEFT JOIN donor ON donor.donor_id = d.donor_id
                        ORDER BY d.created_at DESC, d.donation_id DESC
                    """)
                    donations = cursor.fetchall()
                    self.send_json({"success": True, "donations": donations})
                except Exception as e:
                    print("ADMIN DONATIONS ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load donation records."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/reports":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)

                    cursor.execute("SELECT COUNT(*) AS total FROM donor")
                    total_donors = cursor.fetchone()["total"]
                    cursor.execute("SELECT COUNT(*) AS total FROM ngos")
                    total_ngos = cursor.fetchone()["total"]

                    cursor.execute("""
                        SELECT COUNT(*) AS total,
                               COALESCE(SUM(LOWER(status) IN ('accepted', 'approved')), 0) AS accepted,
                               COALESCE(SUM(LOWER(status) = 'pending'), 0) AS pending,
                               COALESCE(SUM(LOWER(status) = 'rejected'), 0) AS rejected,
                               COALESCE(SUM(DATE(created_at) = CURDATE()), 0) AS today
                        FROM donation
                    """)
                    totals = cursor.fetchone()

                    cursor.execute("""
                        SELECT DATE_FORMAT(created_at, '%M %Y') AS month,
                               DATE_FORMAT(created_at, '%Y-%m') AS month_key,
                               COUNT(*) AS total,
                               COALESCE(SUM(LOWER(status) IN ('accepted', 'approved')), 0) AS accepted,
                               COALESCE(SUM(LOWER(status) = 'pending'), 0) AS pending,
                               COALESCE(SUM(LOWER(status) = 'rejected'), 0) AS rejected
                        FROM donation
                        GROUP BY month_key, month
                        ORDER BY month_key DESC
                        LIMIT 12
                    """)
                    monthly_report = cursor.fetchall()
                    for month in monthly_report:
                        month.pop("month_key", None)

                    self.send_json({
                        "success": True,
                        "total_users": total_donors + total_ngos,
                        "total_donors": total_donors,
                        "total_ngos": total_ngos,
                        "total_donations": totals["total"],
                        "accepted_donations": totals["accepted"],
                        "pending_donations": totals["pending"],
                        "rejected_donations": totals["rejected"],
                        "today_donations": totals["today"],
                        "monthly_report": monthly_report
                    })
                except Exception as e:
                    print("ADMIN REPORTS ERROR:", e)
                    self.send_json({
                        "success": False,
                        "message": "Unable to load report data."
                    }, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path in ("/api/admin/reports/pdf", "/api/admin/reports/excel"):
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("SELECT COUNT(*) AS total FROM donor")
                    total_donors = cursor.fetchone()["total"]
                    cursor.execute("SELECT COUNT(*) AS total FROM ngos")
                    total_ngos = cursor.fetchone()["total"]
                    cursor.execute("""
                        SELECT COUNT(*) AS total,
                               COALESCE(SUM(LOWER(status) IN ('accepted', 'approved')), 0) AS accepted,
                               COALESCE(SUM(LOWER(status) = 'pending'), 0) AS pending,
                               COALESCE(SUM(LOWER(status) = 'rejected'), 0) AS rejected,
                               COALESCE(SUM(DATE(created_at) = CURDATE()), 0) AS today
                        FROM donation
                    """)
                    totals = cursor.fetchone()
                    cursor.execute("""
                        SELECT DATE_FORMAT(created_at, '%M %Y') AS month,
                               DATE_FORMAT(created_at, '%Y-%m') AS month_key,
                               COUNT(*) AS total,
                               COALESCE(SUM(LOWER(status) IN ('accepted', 'approved')), 0) AS accepted,
                               COALESCE(SUM(LOWER(status) = 'pending'), 0) AS pending,
                               COALESCE(SUM(LOWER(status) = 'rejected'), 0) AS rejected
                        FROM donation
                        GROUP BY month_key, month
                        ORDER BY month_key DESC
                        LIMIT 12
                    """)
                    monthly_report = cursor.fetchall()

                    report_rows = [
                        ["HungerFree Donation Report"],
                        ["Total Users", total_donors + total_ngos],
                        ["Total Donors", total_donors],
                        ["Total NGOs", total_ngos],
                        ["Total Donations", totals["total"]],
                        ["Accepted Donations", totals["accepted"]],
                        ["Pending Donations", totals["pending"]],
                        ["Rejected Donations", totals["rejected"]],
                        ["Today's Donations", totals["today"]],
                        [],
                        ["Monthly Donation Report"],
                        ["Month", "Total Donations", "Accepted", "Pending", "Rejected"]
                    ]
                    for month in monthly_report:
                        report_rows.append([
                            month["month"], month["total"], month["accepted"],
                            month["pending"], month["rejected"]
                        ])

                    if request_path.endswith("/pdf"):
                        pdf_lines = ["HungerFree Donation Report", ""]
                        pdf_lines.extend("{}: {}".format(row[0], row[1]) for row in report_rows[1:9])
                        pdf_lines.extend(["", "Monthly Donation Report", "Month | Total | Accepted | Pending | Rejected"])
                        pdf_lines.extend(" | ".join(str(value) for value in row) for row in report_rows[12:])
                        self.send_download(
                            build_report_pdf(pdf_lines), "application/pdf", "hungerfree-report.pdf"
                        )
                    else:
                        excel_rows = []
                        for row in report_rows:
                            excel_rows.append([str(value) if value is not None else "" for value in row])
                        self.send_download(
                            build_report_xlsx(excel_rows),
                            "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                            "hungerfree-report.xlsx"
                        )
                except Exception as e:
                    print("ADMIN REPORT DOWNLOAD ERROR:", e)
                    self.send_json({"success": False, "message": "Unable to generate report download."}, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/feedback":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT feedback_id AS id,
                               user_id,
                               user_name AS name,
                               role,
                               rating,
                               message AS feedback,
                               created_at AS date
                        FROM feedback
                        ORDER BY created_at DESC, feedback_id DESC
                    """)
                    feedback = cursor.fetchall()
                    self.send_json({"success": True, "feedback": feedback})
                except Exception as e:
                    print("ADMIN FEEDBACK ERROR:", e)
                    self.send_json({"success": False, "message": "Unable to load feedback."}, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

            if request_path == "/api/admin/notifications":
                conn = None
                cursor = None
                try:
                    conn = get_connection()
                    cursor = conn.cursor(dictionary=True)
                    cursor.execute("""
                        SELECT notification_id AS id, title, sent_to AS sendTo,
                               created_at AS date, status
                        FROM notification
                        ORDER BY created_at DESC, notification_id DESC
                    """)
                    notifications = cursor.fetchall()
                    self.send_json({"success": True, "notifications": notifications})
                except Exception as e:
                    print("ADMIN NOTIFICATIONS ERROR:", e)
                    self.send_json({"success": False, "message": "Unable to load notifications."}, 500)
                finally:
                    if cursor:
                        cursor.close()
                    if conn:
                        conn.close()
                return

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
        # RECEIVER PROFILE
        # =================================================

        if self.path.startswith("/api/receiver/profile"):
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT
                        ngo_id,
                        organization_name,
                        organization_type,
                        representative_name,
                        email,
                        phone,
                        address,
                        city,
                        location,
                        created_at
                    FROM ngos
                    WHERE ngo_id = %s
                """, (user["user_id"],))
                receiver = cursor.fetchone()

                if not receiver:
                    self.send_json({
                        "success": False,
                        "message": "Receiver not found"
                    }, 404)
                    return

                self.send_json({"success": True, "receiver": receiver})
            except Exception as e:
                print("RECEIVER PROFILE ERROR:", e)
                self.send_json({"success": False, "message": str(e)}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return


        # =================================================
        # RECEIVER AVAILABLE FOOD
        # =================================================

        if self.path.startswith("/api/receiver/available"):
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT
                        d.donation_id,
                        d.food_name,
                        d.food_category,
                        d.quantity,
                        d.cooking_date,
                        d.expiry_time,
                        d.status,
                        d.created_at,
                        donor.resturaent_name AS restaurant,
                        donor.city,
                        donor.address AS pickup_address,
                        COALESCE(NULLIF(d.contact_number, ''), donor.phone) AS contact
                    FROM donation AS d
                    JOIN donor ON donor.donor_id = d.donor_id
                    WHERE LOWER(d.status) = 'pending'
                    ORDER BY d.created_at DESC
                """)
                donations = cursor.fetchall()
                self.send_json({"success": True, "donations": donations})
            except Exception as e:
                print("AVAILABLE FOOD ERROR:", e)
                self.send_json({"success": False, "message": str(e)}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return


        # =================================================
        # RECEIVER ACCEPTED DONATIONS
        # =================================================

        if self.path.startswith("/api/receiver/accepted"):
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT
                        d.donation_id,
                        d.food_name,
                        d.quantity,
                        d.status,
                        d.accepted_at,
                        COALESCE(p.pickup_time, d.pickup_time) AS pickup_time,
                        donor.resturaent_name AS restaurant,
                        COALESCE(NULLIF(d.contact_number, ''), donor.phone) AS contact
                    FROM donation AS d
                    JOIN donor ON donor.donor_id = d.donor_id
                    LEFT JOIN pickup_request AS p
                        ON p.donation_id = d.donation_id
                       AND p.ngo_id = %s
                    WHERE d.ngo_id = %s
                      AND LOWER(d.status) IN ('accepted', 'approved', 'picked up', 'collected', 'completed')
                    ORDER BY d.accepted_at DESC, d.created_at DESC
                """, (user["user_id"], user["user_id"]))
                donations = cursor.fetchall()
                self.send_json({"success": True, "donations": donations})
            except Exception as e:
                print("RECEIVER ACCEPTED DONATIONS ERROR:", e)
                self.send_json({"success": False, "message": str(e)}, 500)
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

        if urlparse(self.path).path.startswith("/api/admin/"):
            user = self.require_role("admin")
            if not user:
                return


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

            cookies = SimpleCookie(self.headers.get("Cookie", ""))
            admin_cookie = cookies.get("admin_session")
            if admin_cookie:
                SESSIONS.pop(admin_cookie.value, None)

            self.send_json({
                "success": True,
                "message": "Logged out"
            }, extra_headers={
                "Set-Cookie": "admin_session=; Path=/; Max-Age=0; HttpOnly; SameSite=Strict"
            })

            return

        request_path = urlparse(self.path).path
        if request_path == "/api/donor/profile/update":
            user = self.require_role("donor")
            if not user:
                return
            fields = {
                "restaurant_name": str(data.get("restaurant_name", "")).strip(),
                "owner_name": str(data.get("owner_name", "")).strip(),
                "email": str(data.get("email", "")).strip(),
                "phone": str(data.get("phone", "")).strip(),
                "address": str(data.get("address", "")).strip(),
                "city": str(data.get("city", "")).strip(),
                "location": str(data.get("location", "")).strip()
            }
            limits = {"restaurant_name": 255, "owner_name": 255, "email": 190,
                      "phone": 30, "city": 100}
            if any(not value for value in fields.values()):
                self.send_json({"success": False, "message": "Please complete all profile fields."}, 400)
                return
            if any(len(fields[key]) > limit for key, limit in limits.items()):
                self.send_json({"success": False, "message": "One or more profile fields are too long."}, 400)
                return
            if "@" not in fields["email"]:
                self.send_json({"success": False, "message": "Enter a valid email address."}, 400)
                return
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    UPDATE donor
                    SET resturaent_name = %s, owner_name = %s, email = %s,
                        phone = %s, address = %s, city = %s, location = %s
                    WHERE donor_id = %s
                """, (
                    fields["restaurant_name"], fields["owner_name"], fields["email"],
                    fields["phone"], fields["address"], fields["city"],
                    fields["location"], user["user_id"]
                ))
                if cursor.rowcount == 0:
                    cursor.execute("SELECT donor_id FROM donor WHERE donor_id = %s", (user["user_id"],))
                    if not cursor.fetchone():
                        self.send_json({"success": False, "message": "Donor account not found."}, 404)
                        return
                conn.commit()
                self.send_json({"success": True, "message": "Profile updated successfully."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("DONOR PROFILE UPDATE ERROR:", e)
                if getattr(e, "errno", None) == 1062:
                    self.send_json({"success": False, "message": "That email address is already in use."}, 409)
                else:
                    self.send_json({"success": False, "message": "Unable to update your profile."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return

        if request_path == "/api/donor/password":
            user = self.require_role("donor")
            if not user:
                return
            current_password = str(data.get("current_password", ""))
            new_password = str(data.get("new_password", ""))
            if not current_password or len(new_password) < 8:
                self.send_json({"success": False, "message": "Enter your current password and a new password of at least 8 characters."}, 400)
                return
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("SELECT password FROM donor WHERE donor_id = %s", (user["user_id"],))
                donor = cursor.fetchone()
                if not donor or not verify_password(current_password, donor["password"]):
                    self.send_json({"success": False, "message": "Current password is incorrect."}, 401)
                    return
                if hmac.compare_digest(current_password, new_password):
                    self.send_json({"success": False, "message": "Choose a new password different from the current one."}, 400)
                    return
                cursor.execute(
                    "UPDATE donor SET password = %s, confirm_password = '' WHERE donor_id = %s",
                    (hash_password(new_password), user["user_id"])
                )
                conn.commit()
                self.send_json({"success": True, "message": "Password changed successfully."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("DONOR PASSWORD CHANGE ERROR:", e)
                self.send_json({"success": False, "message": "Unable to change your password."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return

        if urlparse(self.path).path == "/api/feedback":
            user = self.current_user()
            if not user or user.get("role") not in ("donor", "receiver"):
                self.send_json({"success": False, "message": "Please sign in as a donor or NGO to submit feedback."}, 401)
                return

            message = str(data.get("message", "")).strip()
            try:
                rating = int(data.get("rating", 0))
            except (TypeError, ValueError):
                rating = 0
            if not message:
                self.send_json({"success": False, "message": "Please enter your feedback."}, 400)
                return
            if len(message) > 2000:
                self.send_json({"success": False, "message": "Feedback must be 2,000 characters or fewer."}, 400)
                return
            if rating < 1 or rating > 5:
                self.send_json({"success": False, "message": "Please choose a rating from 1 to 5."}, 400)
                return

            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor(dictionary=True)
                if user["role"] == "donor":
                    cursor.execute("SELECT owner_name AS name FROM donor WHERE donor_id = %s", (user["user_id"],))
                    role = "Donor"
                else:
                    cursor.execute("SELECT representative_name AS name FROM ngos WHERE ngo_id = %s", (user["user_id"],))
                    role = "NGO"
                profile = cursor.fetchone()
                if not profile:
                    self.send_json({"success": False, "message": "Your account could not be found."}, 404)
                    return
                cursor.execute("""
                    INSERT INTO feedback (user_id, user_name, role, rating, message)
                    VALUES (%s, %s, %s, %s, %s)
                """, (user["user_id"], profile["name"], role, rating, message))
                conn.commit()
                self.send_json({"success": True, "message": "Thanks! Your feedback was submitted."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("USER FEEDBACK SUBMISSION ERROR:", e)
                self.send_json({"success": False, "message": "Unable to submit feedback right now."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return

        if urlparse(self.path).path == "/api/admin/feedback/delete":
            conn = None
            cursor = None
            try:
                feedback_id = int(data.get("feedback_id", 0))
                if feedback_id < 1:
                    raise ValueError
            except (TypeError, ValueError):
                self.send_json({"success": False, "message": "A valid feedback ID is required."}, 400)
                return
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("DELETE FROM feedback WHERE feedback_id = %s", (feedback_id,))
                conn.commit()
                self.send_json({"success": True, "message": "Feedback deleted."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("ADMIN FEEDBACK DELETE ERROR:", e)
                self.send_json({"success": False, "message": "Unable to delete feedback."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return

        if urlparse(self.path).path == "/api/admin/notifications":
            title = str(data.get("title", "")).strip()
            sent_to = str(data.get("send_to", "")).strip()
            message = str(data.get("message", "")).strip()
            if not title or len(title) > 255 or not message or sent_to not in ("All Users", "Food Donors", "NGOs"):
                self.send_json({"success": False, "message": "Enter a title, message, and valid recipient."}, 400)
                return
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute("""
                    INSERT INTO notification (title, message, sent_to, status)
                    VALUES (%s, %s, %s, 'Sent')
                """, (title, message, sent_to))
                conn.commit()
                self.send_json({"success": True, "message": "Notification saved."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("ADMIN NOTIFICATION CREATE ERROR:", e)
                self.send_json({"success": False, "message": "Unable to save notification."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return

        delete_path = urlparse(self.path).path
        delete_specs = {
            "/api/admin/donors/delete": ("donor", "donor_id", "donor_id"),
            "/api/admin/ngos/delete": ("ngos", "ngo_id", "ngo_id"),
            "/api/admin/donations/delete": ("donation", "donation_id", "donation_id"),
            "/api/admin/notifications/delete": ("notification", "notification_id", "notification_id"),
        }
        if delete_path == "/api/admin/users/delete":
            user_id = str(data.get("user_id", "")).strip()
            if user_id.upper().startswith("DN"):
                delete_spec = ("donor", "donor_id", user_id)
            elif user_id.upper().startswith("RN"):
                delete_spec = ("ngos", "ngo_id", user_id)
            else:
                self.send_json({"success": False, "message": "A valid donor or NGO user ID is required."}, 400)
                return
        elif delete_path in delete_specs:
            table, column, body_key = delete_specs[delete_path]
            delete_value = data.get(body_key)
            if table in ("donation", "notification") and delete_value is not None:
                try:
                    delete_value = int(delete_value)
                except (TypeError, ValueError):
                    delete_value = None
            if delete_value is None or str(delete_value).strip() == "":
                self.send_json({"success": False, "message": "A valid record ID is required."}, 400)
                return
            delete_spec = (table, column, delete_value)
        else:
            delete_spec = None

        if delete_spec:
            table, column, delete_value = delete_spec
            conn = None
            cursor = None
            try:
                conn = get_connection()
                cursor = conn.cursor()
                cursor.execute(
                    "DELETE FROM `{}` WHERE `{}` = %s".format(table, column),
                    (delete_value,)
                )
                if cursor.rowcount == 0:
                    conn.rollback()
                    self.send_json({"success": False, "message": "The selected record was not found."}, 404)
                    return
                conn.commit()
                self.send_json({"success": True, "message": "Record deleted successfully."})
            except Exception as e:
                if conn:
                    conn.rollback()
                print("ADMIN DELETE ERROR:", e)
                self.send_json({"success": False, "message": "Unable to delete this record."}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
            return


        # =================================================
        # RECEIVER ACCEPTS A DONATION
        # =================================================

        if self.path == "/api/receiver/accept":
            user = self.require_role("receiver")
            if not user:
                return

            try:
                donation_id = int(data.get("donation_id"))
                if donation_id <= 0:
                    raise ValueError
            except (TypeError, ValueError):
                self.send_json({
                    "success": False,
                    "message": "A valid donation ID is required."
                }, 400)
                return

            conn = None
            cursor = None
            try:
                conn = get_connection()
                conn.start_transaction()
                cursor = conn.cursor(dictionary=True)
                cursor.execute("""
                    SELECT donation_id, status
                    FROM donation
                    WHERE donation_id = %s
                    FOR UPDATE
                """, (donation_id,))
                donation = cursor.fetchone()

                if not donation:
                    conn.rollback()
                    self.send_json({"success": False, "message": "Donation not found."}, 404)
                    return

                if str(donation["status"]).strip().lower() != "pending":
                    conn.rollback()
                    self.send_json({
                        "success": False,
                        "message": "This donation is no longer available. Refresh the list."
                    }, 409)
                    return

                cursor.execute("""
                    SELECT
                        d.donation_id,
                        d.food_name,
                        d.quantity,
                        donor.resturaent_name,
                        donor.email,
                        donor.phone,
                        donor.address
                    FROM donation AS d
                    JOIN donor ON donor.donor_id = d.donor_id
                    WHERE d.donation_id = %s
                """, (donation_id,))
                donation_details = cursor.fetchone()

                cursor.execute("""
                    SELECT ngo_id, organization_name, representative_name, email, phone
                    FROM ngos
                    WHERE ngo_id = %s
                """, (user["user_id"],))
                receiver_details = cursor.fetchone()

                if not donation_details or not receiver_details:
                    conn.rollback()
                    self.send_json({
                        "success": False,
                        "message": "Donation or receiver account details could not be found."
                    }, 404)
                    return

                cursor.execute("""
                    INSERT INTO pickup_request (donation_id, ngo_id, status)
                    VALUES (%s, %s, 'Accepted')
                """, (donation_id, user["user_id"]))
                cursor.execute("""
                    UPDATE donation
                    SET ngo_id = %s, status = 'Accepted', accepted_at = NOW()
                    WHERE donation_id = %s AND LOWER(status) = 'pending'
                """, (user["user_id"], donation_id))

                if cursor.rowcount != 1:
                    conn.rollback()
                    self.send_json({
                        "success": False,
                        "message": "This donation was accepted by another receiver. Refresh the list."
                    }, 409)
                    return

                conn.commit()

                cursor.close()
                cursor = None
                conn.close()
                conn = None

                email_results = send_acceptance_emails(
                    donation_details,
                    {
                        "resturaent_name": donation_details["resturaent_name"],
                        "email": donation_details["email"],
                        "phone": donation_details["phone"],
                        "address": donation_details["address"]
                    },
                    receiver_details
                )
                for recipient, result in email_results.items():
                    if not result["sent"]:
                        print(
                            "ACCEPTANCE EMAIL NOT SENT TO {}: {}".format(
                                recipient, result.get("reason", "Unknown error")
                            )
                        )

                all_emails_sent = all(
                    result["sent"] for result in email_results.values()
                )
                self.send_json({
                    "success": True,
                    "message": (
                        "Food accepted successfully. Email notifications sent."
                        if all_emails_sent
                        else "Food accepted successfully, but email notifications could not be sent. Check SMTP settings."
                    ),
                    "donation_id": donation_id,
                    "email_notifications": email_results
                })
            except Exception as e:
                if conn:
                    conn.rollback()
                print("RECEIVER ACCEPT ERROR:", e)
                self.send_json({"success": False, "message": str(e)}, 500)
            finally:
                if cursor:
                    cursor.close()
                if conn:
                    conn.close()
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
                        ngo_id,

                    "receiver_id":
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


                if not password:

                    self.send_json({
                        "success": False,
                        "message": "Please enter Password."
                    }, 400)

                    return


                if userid.startswith("AD") and not username:

                    self.send_json({
                        "success": False,
                        "message": "Please enter Admin User Name."
                    }, 400)

                    return


                if userid.startswith("AD") and not email:

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
                # ADMIN LOGIN
                # =========================================

                if userid.startswith("AD") or userid == "ADMIN90":

                    # Keep the legacy bootstrap account available only for
                    # its established fixed credentials. Normal AD... admins
                    # authenticate against the admin record in the database.
                    legacy_bootstrap_match = (
                        userid == "ADMIN90"
                        and username.casefold() == "adminsite"
                        and email.casefold() == "rajeshwarinair827@gmail.com"
                        and hmac.compare_digest(password, "admin123")
                    )

                    cursor.execute("SHOW COLUMNS FROM admin")
                    admin_columns = {column["Field"] for column in cursor.fetchall()}
                    name_column = next(
                        (column for column in ("username", "admin_name", "user_name")
                         if column in admin_columns),
                        None
                    )
                    if not name_column:
                        cursor.close()
                        conn.close()
                        self.send_json({
                            "success": False,
                            "message": "The admin table must have a username or admin_name column."
                        }, 500)
                        return

                    cursor.execute("""
                        SELECT admin_id, `{}` AS username, email, password, role,
                               last_login, created_at
                        FROM admin
                        WHERE admin_id = %s
                          AND `{}` = %s
                          AND email = %s
                    """.format(name_column, name_column),
                    (userid, username, email))
                    admin = cursor.fetchone()

                    if not admin:
                        if not legacy_bootstrap_match:
                            cursor.close()
                            conn.close()
                            self.send_json({
                                "success": False,
                                "message": "Admin details do not match. Check your Admin ID, name, password, and email."
                            }, 401)
                            return

                        cursor.execute("""
                            SELECT admin_id
                            FROM admin
                            WHERE admin_id = %s OR `{}` = %s OR email = %s
                            LIMIT 1
                        """.format(name_column),
                        (userid, username, email))
                        conflicting_admin = cursor.fetchone()

                        if conflicting_admin:
                            cursor.close()
                            conn.close()
                            self.send_json({
                                "success": False,
                                "message": "The configured admin ID, username, or email is already assigned to another admin account."
                            }, 409)
                            return

                        cursor.execute("""
                            INSERT INTO admin (admin_id, `{}`, email, password, role)
                            VALUES (%s, %s, %s, %s, 'Admin')
                        """.format(name_column), (
                            userid,
                            username,
                            email,
                            hash_password(password)
                        ))
                        conn.commit()
                        cursor.execute("""
                            SELECT admin_id, `{}` AS username, email, password, role,
                                   last_login, created_at
                            FROM admin
                            WHERE admin_id = %s
                        """.format(name_column), (userid,))
                        admin = cursor.fetchone()

                    stored_password = admin.pop("password", None) if admin else None
                    if not admin or not verify_password(password, stored_password):
                        cursor.close()
                        conn.close()
                        self.send_json({
                            "success": False,
                            "message": "Admin details do not match."
                        }, 401)
                        return

                    if not is_hashed(stored_password):
                        cursor.execute(
                            "UPDATE admin SET password = %s WHERE admin_id = %s",
                            (hash_password(password), admin["admin_id"])
                        )

                    cursor.execute(
                        "UPDATE admin SET last_login = NOW() WHERE admin_id = %s",
                        (admin["admin_id"],)
                    )
                    conn.commit()
                    token = create_session(admin["admin_id"], "admin")

                    cursor.close()
                    conn.close()

                    self.send_json({
                        "success": True,
                        "message": "Admin Login Successful",
                        "role": "admin",
                        "token": token,
                        "user_id": admin["admin_id"],
                        "user": admin
                    }, extra_headers={
                        "Set-Cookie": (
                            "admin_session={}; Path=/; Max-Age={}; HttpOnly; SameSite=Strict"
                        ).format(token, SESSION_TTL)
                    })
                    return


                # =========================================
                # DONOR LOGIN
                # =========================================

                elif userid.startswith("DN"):

                    cursor.execute("""
                        SELECT
                            donor_id,
                            owner_name,
                            email,
                            resturaent_name,
                            password
                        FROM donor
                        WHERE donor_id = %s
                    """, (userid,))


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

                        }, extra_headers=self.expire_admin_cookie())


                        return


                    else:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": False,

                            "message":
                                "Donor ID or password is incorrect."

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
                    """, (userid,))


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

                        }, extra_headers=self.expire_admin_cookie())


                        return


                    else:

                        cursor.close()
                        conn.close()


                        self.send_json({

                            "success": False,

                            "message":
                                "Receiver ID or password is incorrect."

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
                            "Invalid User ID. Admin IDs start with AD, Donor IDs with DN, and Receiver IDs with RN."

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
