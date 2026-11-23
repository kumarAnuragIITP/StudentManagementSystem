# =========================================================
# FILE: student_panel.py
# =========================================================
# FULLY WORKING
# FLET 0.80.0
# FILE PICKER IMAGE UPLOAD
# =========================================================

import flet as ft
from pymongo import MongoClient
from datetime import datetime
import os


# =========================================================
# DATABASE
# =========================================================

class StudentDB:

    def __init__(self):

        self.client = MongoClient(
            "mongodb://localhost:27017/"
        )

        self.db = self.client["student_management"]

        self.students = self.db["students"]

    def add_student(self, data):

        existing = self.students.find_one({
            "roll": data["roll"]
        })

        if existing:
            return False

        self.students.insert_one(data)

        return True

    def get_student(self, roll):

        return self.students.find_one({
            "roll": roll
        })


# =========================================================
# MAIN PANEL
# =========================================================

class StudentPanel:

    def __init__(self, page: ft.Page):

        self.page = page

        self.db = StudentDB()

        self.selected_photo = ""

        self.setup_page()

        # =================================================
        # FILE PICKER
        # =================================================

        self.file_picker = ft.FilePicker(
            on_result=self.on_file_selected
        )

        self.page.overlay.append(
            self.file_picker
        )

        self.build_ui()

    # =====================================================
    # PAGE SETUP
    # =====================================================

    def setup_page(self):

        self.page.title = "Student Panel"

        self.page.theme_mode = ft.ThemeMode.DARK

        self.page.bgcolor = "#0F172A"

        self.page.padding = 20

        self.page.scroll = ft.ScrollMode.AUTO

        self.page.window_width = 1400

        self.page.window_height = 900

    # =====================================================
    # MESSAGE
    # =====================================================

    def show_message(self, text):

        self.page.snack_bar = ft.SnackBar(
            content=ft.Text(text)
        )

        self.page.snack_bar.open = True

        self.page.update()

    # =====================================================
    # INPUT
    # =====================================================

    def create_input(self, label, icon):

        return ft.TextField(
            label=label,
            prefix_icon=icon,
            border_radius=12,
            filled=True,
            bgcolor="#1E293B",
            border_color="#334155",
            color="white"
        )

    # =====================================================
    # OPEN FILE PICKER
    # =====================================================

    def upload_photo_action(self, e):

        self.file_picker.pick_files(
            allow_multiple=False,
            allowed_extensions=[
                "png",
                "jpg",
                "jpeg",
                "webp"
            ]
        )

    # =====================================================
    # FILE SELECTED
    # =====================================================

    def on_file_selected(self, e: ft.FilePickerUploadEvent):

        if e.files:

            file = e.files[0]

            self.selected_photo = file.path

            self.photo_text.value = file.name

            self.photo_preview.src = file.path

            self.photo_preview.visible = True

            self.page.update()

            self.show_message(
                "Photo Selected Successfully"
            )

        else:

            self.show_message(
                "No File Selected"
            )

    # =====================================================
    # CREATE PROFILE
    # =====================================================

    def create_profile(self, e):

        if not all([

            self.name.value,
            self.roll.value,
            self.mobile.value,
            self.department.value,
            self.address.value

        ]):

            self.show_message(
                "All Fields Required"
            )

            return

        data = {

            "name": self.name.value,

            "roll": self.roll.value,

            "mobile": self.mobile.value,

            "department": self.department.value,

            "address": self.address.value,

            "photo": self.selected_photo,

            "attendance": "92%",

            "fees_status": "Paid",

            "library_books": 2,

            "created_at": str(datetime.now())
        }

        result = self.db.add_student(data)

        if not result:

            self.show_message(
                "Student Already Exists"
            )

            return

        self.show_message(
            "Profile Created Successfully"
        )

    # =====================================================
    # LOAD STUDENT
    # =====================================================

    def load_student_data(self):

        roll = self.roll.value.strip()

        if not roll:

            self.show_message(
                "Enter Roll Number"
            )

            return

        student = self.db.get_student(roll)

        if not student:

            self.show_message(
                "Student Not Found"
            )

            return

        self.profile_name.value = (
            f"Name : {student.get('name', '')}"
        )

        self.profile_roll.value = (
            f"Roll : {student.get('roll', '')}"
        )

        self.profile_mobile.value = (
            f"Mobile : {student.get('mobile', '')}"
        )

        self.profile_department.value = (
            f"Department : {student.get('department', '')}"
        )

        self.profile_address.value = (
            f"Address : {student.get('address', '')}"
        )

        self.profile_attendance.value = (
            student.get("attendance", "")
        )

        self.profile_fees.value = (
            student.get("fees_status", "")
        )

        self.profile_books.value = str(
            student.get("library_books", 0)
        )

        photo = student.get("photo")

        if photo and os.path.exists(photo):

            self.student_image.src = photo

        else:

            self.student_image.src = ""

        self.page.update()

    # =====================================================
    # UI
    # =====================================================

    def build_ui(self):

        self.name = self.create_input(
            "Student Name",
            ft.Icons.PERSON
        )

        self.roll = self.create_input(
            "Roll Number",
            ft.Icons.BADGE
        )

        self.mobile = self.create_input(
            "Mobile Number",
            ft.Icons.PHONE
        )

        self.department = self.create_input(
            "Department",
            ft.Icons.SCHOOL
        )

        self.address = self.create_input(
            "Address",
            ft.Icons.LOCATION_ON
        )

        # =================================================
        # PHOTO
        # =================================================

        self.photo_text = ft.Text(
            "No Photo Selected",
            color="white"
        )

        self.photo_preview = ft.Image(
            src="",
            width=120,
            height=120,
            border_radius=15,
            visible=False,
            fit="cover"
        )

        # =================================================
        # PROFILE
        # =================================================

        self.profile_name = ft.Text(
            "",
            size=18,
            color="white"
        )

        self.profile_roll = ft.Text(
            "",
            size=18,
            color="white"
        )

        self.profile_mobile = ft.Text(
            "",
            size=18,
            color="white"
        )

        self.profile_department = ft.Text(
            "",
            size=18,
            color="white"
        )

        self.profile_address = ft.Text(
            "",
            size=18,
            color="white"
        )

        self.profile_attendance = ft.Text(
            "",
            size=18,
            color="#10B981"
        )

        self.profile_fees = ft.Text(
            "",
            size=18,
            color="#F59E0B"
        )

        self.profile_books = ft.Text(
            "",
            size=18,
            color="#38BDF8"
        )

        self.student_image = ft.Image(
            src="",
            width=140,
            height=140,
            border_radius=100,
            fit="cover"
        )

        # =================================================
        # LEFT PANEL
        # =================================================

        left_panel = ft.Container(

            bgcolor="#111827",

            border_radius=20,

            padding=25,

            content=ft.Column(

                spacing=15,

                controls=[

                    ft.Text(
                        "Student Registration",
                        size=28,
                        weight=ft.FontWeight.BOLD,
                        color="white"
                    ),

                    self.name,

                    self.roll,

                    self.mobile,

                    self.department,

                    self.address,

                    ft.Row(

                        controls=[

                            ft.ElevatedButton(

                                "Upload Photo",

                                icon=ft.Icons.UPLOAD,

                                style=ft.ButtonStyle(
                                    bgcolor="#2563EB",
                                    color="white"
                                ),

                                on_click=self.upload_photo_action
                            ),

                            self.photo_text
                        ]
                    ),

                    self.photo_preview,

                    ft.ElevatedButton(

                        "Create Student Profile",

                        width=350,

                        height=50,

                        style=ft.ButtonStyle(
                            bgcolor="#6C63FF",
                            color="white"
                        ),

                        on_click=self.create_profile
                    ),

                    ft.OutlinedButton(

                        "Load Student Dashboard",

                        width=350,

                        on_click=lambda e:
                        self.load_student_data()
                    )
                ]
            )
        )

        # =================================================
        # RIGHT PANEL
        # =================================================

        right_panel = ft.Container(

            bgcolor="#111827",

            border_radius=20,

            padding=25,

            content=ft.Column(

                spacing=20,

                controls=[

                    ft.Text(
                        "Student Dashboard",
                        size=30,
                        weight=ft.FontWeight.BOLD,
                        color="white"
                    ),

                    self.student_image,

                    ft.Divider(),

                    self.profile_name,
                    self.profile_roll,
                    self.profile_mobile,
                    self.profile_department,
                    self.profile_address,

                    ft.Divider(),

                    ft.Row([
                        ft.Text(
                            "Attendance : ",
                            color="white"
                        ),
                        self.profile_attendance
                    ]),

                    ft.Row([
                        ft.Text(
                            "Fees Status : ",
                            color="white"
                        ),
                        self.profile_fees
                    ]),

                    ft.Row([
                        ft.Text(
                            "Library Books : ",
                            color="white"
                        ),
                        self.profile_books
                    ])
                ]
            )
        )

        # =================================================
        # PAGE
        # =================================================

        self.page.add(

            ft.Column(

                controls=[

                    ft.Text(
                        "Professional Student Management System",
                        size=34,
                        weight=ft.FontWeight.BOLD,
                        color="white"
                    ),

                    ft.Text(
                        "Flet 0.80.0 Compatible",
                        color="#94A3B8"
                    ),

                    ft.Container(height=15),

                    ft.ResponsiveRow(

                        controls=[

                            ft.Container(
                                content=left_panel,
                                col={"xs": 12, "md": 4}
                            ),

                            ft.Container(
                                content=right_panel,
                                col={"xs": 12, "md": 8}
                            ),
                        ]
                    )
                ]
            )
        )


# =========================================================
# MAIN
# =========================================================

def main(page: ft.Page):

    StudentPanel(page)


# =========================================================
# RUN
# =========================================================

ft.run(main)