# =========================================================
# FILE: admin_panel.py
# =========================================================
# MODERN FULL-PAGE STUDENT MANAGEMENT DASHBOARD
#
# IMPORTANT:
# - NO VISIBLE SCROLLBAR
# - WHOLE PAGE SCROLLS
# - MOUSE WHEEL / TOUCHPAD SCROLL
# - PAGEUP / PAGEDOWN / HOME / END
# - COMPLETE FORM
# - COMPLETE STUDENT DIRECTORY
# - SEARCH
# - PHOTO UPLOAD
# - ADD
# - DELETE
# - CRUD
# =========================================================

import tkinter as tk
from tkinter import filedialog, messagebox, ttk
from PIL import Image, ImageTk
from pymongo import MongoClient
from datetime import datetime
import os
import shutil


# =========================================================
# COLORS
# =========================================================

BACKGROUND = "#F5F7FB"
SURFACE = "#FFFFFF"
SURFACE_2 = "#F8FAFC"

PRIMARY = "#6D28D9"
PRIMARY_HOVER = "#5B21B6"

SUCCESS = "#059669"
DANGER = "#DC2626"
WARNING = "#D97706"

TEXT = "#111827"
TEXT_2 = "#374151"
MUTED = "#6B7280"
LIGHT_TEXT = "#9CA3AF"

BORDER = "#E5E7EB"
INPUT_BG = "#F9FAFB"

WHITE = "#FFFFFF"


# =========================================================
# DATABASE
# =========================================================

client = MongoClient(
    "mongodb://localhost:27017/"
)

db = client["student_management"]

students_collection = db["students"]


# =========================================================
# MAIN CLASS
# =========================================================

class StudentManagementApp:

    def __init__(self, parent, session=None):

        self.parent = parent
        self.session = session or {}

        self.selected_image_path = None
        self.image_preview = None

        self.entries = {}

        self.build_ui()
        self.load_students()

    # =====================================================
    # CLEAR
    # =====================================================

    def clear_parent(self):

        for widget in self.parent.winfo_children():
            widget.destroy()

    # =====================================================
    # MAIN UI
    # =====================================================

    def build_ui(self):

        self.clear_parent()

        self.parent.configure(
            bg=BACKGROUND
        )

        # =================================================
        # ROOT CANVAS
        #
        # NO VISIBLE SCROLLBAR
        # =================================================

        self.canvas = tk.Canvas(
            self.parent,
            bg=BACKGROUND,
            highlightthickness=0,
            bd=0
        )

        self.canvas.pack(
            fill="both",
            expand=True
        )

        # =================================================
        # COMPLETE PAGE
        # =================================================

        self.page = tk.Frame(
            self.canvas,
            bg=BACKGROUND
        )

        self.canvas_window = self.canvas.create_window(
            (0, 0),
            window=self.page,
            anchor="nw"
        )

        # =================================================
        # SCROLL CONFIGURATION
        # =================================================

        self.page.bind(
            "<Configure>",
            self.update_scroll_region
        )

        self.canvas.bind(
            "<Configure>",
            self.resize_page
        )

        # =================================================
        # MOUSE / TOUCHPAD SCROLL
        # =================================================

        self.canvas.bind_all(
            "<MouseWheel>",
            self.mousewheel,
            add="+"
        )



        # Linux
        self.canvas.bind_all(
            "<Button-4>",
            self.scroll_up
        )

        self.canvas.bind_all(
            "<Button-5>",
            self.scroll_down
        )

        # Keyboard navigation
        self.canvas.bind_all(
            "<Prior>",
            self.page_up
        )

        self.canvas.bind_all(
            "<Next>",
            self.page_down
        )

        self.canvas.bind_all(
            "<Home>",
            self.page_home
        )

        self.canvas.bind_all(
            "<End>",
            self.page_end
        )

        # =================================================
        # BUILD COMPLETE PAGE
        # =================================================

        self.build_header()

        self.build_welcome()

        self.build_registration_section()

        self.build_student_directory()

        # Bottom spacing
        tk.Frame(
            self.page,
            bg=BACKGROUND,
            height=60
        ).pack(
            fill="x"
        )

    # =====================================================
    # SCROLL SYSTEM
    # =====================================================

    def update_scroll_region(self, event=None):

        self.canvas.configure(
            scrollregion=self.canvas.bbox("all")
        )

    def resize_page(self, event):

        self.canvas.itemconfigure(
            self.canvas_window,
            width=event.width
        )

        self.update_scroll_region()

    # =====================================================
    # TOUCHPAD / MOUSE SCROLLING
    # =====================================================

    # =====================================================
    # SMOOTH MOUSE + TWO-FINGER TOUCHPAD SCROLLING
    # =====================================================

    def mousewheel(self, event):
        """
        Smooth mouse wheel + two-finger touchpad scrolling for Windows/Mac/Linux.
        """
        # On Windows, event.delta is typically a multiple of 120.
        # Precision touchpads provide smaller values.
        if event.delta:
            # For Windows / macOS
            amount = int(-1 * (event.delta / 120))
            if amount == 0:
                amount = -1 if event.delta > 0 else 1
            self.canvas.yview_scroll(amount, "units")
        elif hasattr(event, 'num'):
            # For Linux button-4 / button-5
            if event.num == 4:
                self.canvas.yview_scroll(-3, "units")
            elif event.num == 5:
                self.canvas.yview_scroll(3, "units")

        return "break"

    def scroll_down(self, event=None):

        self.canvas.yview_scroll(
            3,
            "units"
        )

        return "break"

    def scroll_up(self, event):

        self.canvas.yview_scroll(
            -3,
            "units"
        )

    def scroll_down(self, event):

        self.canvas.yview_scroll(
            3,
            "units"
        )

    def page_up(self, event):

        self.canvas.yview_scroll(
            -8,
            "units"
        )

    def page_down(self, event):

        self.canvas.yview_scroll(
            8,
            "units"
        )

    def page_home(self, event):

        self.canvas.yview_moveto(0)

    def page_end(self, event):

        self.canvas.yview_moveto(1)

    # =====================================================
    # HEADER
    # =====================================================

    def build_header(self):

        header = tk.Frame(
            self.page,
            bg=SURFACE,
            height=86,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        header.pack(
            fill="x",
            padx=28,
            pady=(25, 8)
        )

        header.pack_propagate(False)

        # Left
        left = tk.Frame(
            header,
            bg=SURFACE
        )

        left.pack(
            side="left",
            padx=22,
            pady=12
        )

        tk.Label(
            left,
            text="STUDENT",
            bg=SURFACE,
            fg=PRIMARY,
            font=("Segoe UI", 10, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            left,
            text="Management Dashboard",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 22, "bold")
        ).pack(
            anchor="w"
        )

        # Right status
        status = tk.Frame(
            header,
            bg="#F0FDF4",
            highlightbackground="#BBF7D0",
            highlightthickness=1
        )

        status.pack(
            side="right",
            padx=22,
            pady=20
        )

        tk.Label(
            status,
            text="●  SYSTEM ACTIVE",
            bg="#F0FDF4",
            fg=SUCCESS,
            font=("Segoe UI", 9, "bold"),
            padx=14,
            pady=8
        ).pack()

    # =====================================================
    # WELCOME
    # =====================================================

    def build_welcome(self):

        wrapper = tk.Frame(
            self.page,
            bg=BACKGROUND
        )

        wrapper.pack(
            fill="x",
            padx=32,
            pady=(12, 22)
        )

        tk.Label(
            wrapper,
            text="Student Administration",
            bg=BACKGROUND,
            fg=TEXT,
            font=("Segoe UI", 30, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            wrapper,
            text=(
                "Register students, manage records, upload photographs "
                "and search the complete student database from one page."
            ),
            bg=BACKGROUND,
            fg=MUTED,
            font=("Segoe UI", 12)
        ).pack(
            anchor="w",
            pady=(5, 0)
        )

    # =====================================================
    # REGISTRATION SECTION
    # =====================================================

    def build_registration_section(self):

        outer = tk.Frame(
            self.page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        outer.pack(
            fill="x",
            padx=28,
            pady=10
        )

        # =================================================
        # SECTION HEADER
        # =================================================

        section_header = tk.Frame(
            outer,
            bg=SURFACE
        )

        section_header.pack(
            fill="x",
            padx=25,
            pady=(22, 10)
        )

        tk.Label(
            section_header,
            text="01",
            bg=PRIMARY,
            fg=WHITE,
            font=("Segoe UI", 10, "bold"),
            width=4,
            pady=6
        ).pack(
            side="left"
        )

        title_box = tk.Frame(
            section_header,
            bg=SURFACE
        )

        title_box.pack(
            side="left",
            padx=12
        )

        tk.Label(
            title_box,
            text="Student Registration",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 19, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            title_box,
            text="Enter complete student information below",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(
            anchor="w"
        )

        # =================================================
        # FORM CONTENT
        # =================================================

        form = tk.Frame(
            outer,
            bg=SURFACE
        )

        form.pack(
            fill="x",
            padx=25,
            pady=(5, 25)
        )

        # -------------------------------------------------
        # BASIC INFORMATION
        # -------------------------------------------------

        self.section_title(
            form,
            "Basic Information",
            "Student identity and personal details"
        )

        basic = tk.Frame(
            form,
            bg=SURFACE
        )

        basic.pack(
            fill="x",
            pady=(12, 20)
        )

        self.sid = self.form_entry(
            basic,
            "Student ID *",
            0,
            0
        )

        self.roll = self.form_entry(
            basic,
            "Roll Number *",
            0,
            1
        )

        self.name = self.form_entry(
            basic,
            "Student Full Name *",
            0,
            2
        )

        self.father_name = self.form_entry(
            basic,
            "Father Name *",
            1,
            0
        )

        self.mother_name = self.form_entry(
            basic,
            "Mother Name",
            1,
            1
        )

        self.gender = self.form_combo(
            basic,
            "Gender *",
            ["Male", "Female", "Other"],
            1,
            2
        )

        self.dob = self.form_entry(
            basic,
            "Date Of Birth",
            2,
            0
        )

        self.age = self.form_entry(
            basic,
            "Age",
            2,
            1
        )

        self.marital_status = self.form_combo(
            basic,
            "Marital Status",
            ["Single", "Married"],
            2,
            2
        )

        self.address = self.form_entry(
            basic,
            "Address",
            3,
            0,
            colspan=3
        )

        # -------------------------------------------------
        # ACADEMIC INFORMATION
        # -------------------------------------------------

        self.section_title(
            form,
            "Academic Information",
            "College, course, branch and semester details"
        )

        academic = tk.Frame(
            form,
            bg=SURFACE
        )

        academic.pack(
            fill="x",
            pady=(12, 20)
        )

        self.college = self.form_entry(
            academic,
            "College Name *",
            0,
            0
        )

        self.department = self.form_entry(
            academic,
            "Department",
            0,
            1
        )

        self.branch = self.form_entry(
            academic,
            "Branch Name *",
            0,
            2
        )

        self.course = self.form_entry(
            academic,
            "Course Name",
            1,
            0
        )

        self.semester = self.form_combo(
            academic,
            "Semester *",
            [
                "1", "2", "3", "4",
                "5", "6", "7", "8"
            ],
            1,
            1
        )

        self.blood_group = self.form_combo(
            academic,
            "Blood Group",
            [
                "A+", "A-",
                "B+", "B-",
                "AB+", "AB-",
                "O+", "O-"
            ],
            1,
            2
        )

        self.admission_date = self.form_entry(
            academic,
            "Date Of Admission",
            2,
            0
        )

        self.exit_date = self.form_entry(
            academic,
            "Exit Date",
            2,
            1
        )

        # -------------------------------------------------
        # CONTACT INFORMATION
        # -------------------------------------------------

        self.section_title(
            form,
            "Contact Information",
            "Student and parent contact details"
        )

        contact = tk.Frame(
            form,
            bg=SURFACE
        )

        contact.pack(
            fill="x",
            pady=(12, 20)
        )

        self.email = self.form_entry(
            contact,
            "Email ID *",
            0,
            0
        )

        self.mobile = self.form_entry(
            contact,
            "Student Mobile Number *",
            0,
            1
        )

        self.parent_mobile = self.form_entry(
            contact,
            "Parents Mobile Number",
            0,
            2
        )

        self.linkedin = self.form_entry(
            contact,
            "LinkedIn ID",
            1,
            0,
            colspan=3
        )

        # -------------------------------------------------
        # PHOTO
        # -------------------------------------------------

        self.section_title(
            form,
            "Student Photograph",
            "Upload the student's profile photograph"
        )

        photo_area = tk.Frame(
            form,
            bg=SURFACE_2,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        photo_area.pack(
            fill="x",
            pady=(12, 20)
        )

        photo_left = tk.Frame(
            photo_area,
            bg=SURFACE_2
        )

        photo_left.pack(
            side="left",
            padx=20,
            pady=18
        )

        self.preview_label = tk.Label(
            photo_left,
            text="PHOTO\nPREVIEW",
            bg="#EEF2FF",
            fg=PRIMARY,
            width=16,
            height=8,
            font=("Segoe UI", 9, "bold")
        )

        self.preview_label.pack()

        photo_right = tk.Frame(
            photo_area,
            bg=SURFACE_2
        )

        photo_right.pack(
            side="left",
            padx=20,
            pady=20,
            fill="x",
            expand=True
        )

        tk.Label(
            photo_right,
            text="Student Photo Upload *",
            bg=SURFACE_2,
            fg=TEXT,
            font=("Segoe UI", 12, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            photo_right,
            text="PNG, JPG or JPEG • Recommended square image",
            bg=SURFACE_2,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(4, 12)
        )

        tk.Button(
            photo_right,
            text="  UPLOAD STUDENT PHOTO  ",
            command=self.select_image,
            bg=PRIMARY,
            fg=WHITE,
            activebackground=PRIMARY_HOVER,
            activeforeground=WHITE,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=10,
            pady=10
        ).pack(
            anchor="w"
        )

        # -------------------------------------------------
        # ACTIONS
        # -------------------------------------------------

        actions = tk.Frame(
            form,
            bg=SURFACE
        )

        actions.pack(
            fill="x",
            pady=(5, 5)
        )

        tk.Button(
            actions,
            text="AI VALIDATE REQUIRED FIELDS",
            command=self.validate_fields,
            bg="#FEF3C7",
            fg="#92400E",
            activebackground="#FDE68A",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=12
        ).pack(
            side="left",
            padx=(0, 10)
        )

        tk.Button(
            actions,
            text="ENABLE CRUD OPERATIONS",
            command=self.enable_crud,
            bg="#EDE9FE",
            fg="#5B21B6",
            activebackground="#DDD6FE",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=18,
            pady=12
        ).pack(
            side="left"
        )

        # Main actions on right
        tk.Button(
            actions,
            text="DELETE STUDENT",
            command=self.delete_student,
            bg="#FEE2E2",
            fg=DANGER,
            activebackground="#FECACA",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=12
        ).pack(
            side="right"
        )

        tk.Button(
            actions,
            text="ADD STUDENT",
            command=self.add_student,
            bg=SUCCESS,
            fg=WHITE,
            activebackground="#047857",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 11, "bold"),
            padx=28,
            pady=12
        ).pack(
            side="right",
            padx=10
        )

    # =====================================================
    # SECTION TITLE
    # =====================================================

    def section_title(
        self,
        parent,
        title,
        subtitle
    ):

        box = tk.Frame(
            parent,
            bg=SURFACE
        )

        box.pack(
            fill="x",
            pady=(12, 0)
        )

        tk.Label(
            box,
            text=title,
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            box,
            text=subtitle,
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(
            anchor="w",
            pady=(2, 0)
        )

        tk.Frame(
            box,
            bg=BORDER,
            height=1
        ).pack(
            fill="x",
            pady=(9, 0)
        )

    # =====================================================
    # FORM ENTRY
    # =====================================================

    def form_entry(
        self,
        parent,
        label,
        row,
        column,
        colspan=1
    ):

        box = tk.Frame(
            parent,
            bg=SURFACE
        )

        box.grid(
            row=row,
            column=column,
            columnspan=colspan,
            sticky="ew",
            padx=6,
            pady=6
        )

        parent.grid_columnconfigure(
            column,
            weight=1
        )

        tk.Label(
            box,
            text=label,
            bg=SURFACE,
            fg=TEXT_2,
            font=("Segoe UI", 9, "bold")
        ).pack(
            anchor="w",
            pady=(0, 5)
        )

        entry = tk.Entry(
            box,
            bg=INPUT_BG,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            highlightcolor=PRIMARY,
            font=("Segoe UI", 10)
        )

        entry.pack(
            fill="x",
            ipady=9
        )

        return entry

    # =====================================================
    # FORM COMBO
    # =====================================================

    def form_combo(
        self,
        parent,
        label,
        values,
        row,
        column,
        colspan=1
    ):

        box = tk.Frame(
            parent,
            bg=SURFACE
        )

        box.grid(
            row=row,
            column=column,
            columnspan=colspan,
            sticky="ew",
            padx=6,
            pady=6
        )

        parent.grid_columnconfigure(
            column,
            weight=1
        )

        tk.Label(
            box,
            text=label,
            bg=SURFACE,
            fg=TEXT_2,
            font=("Segoe UI", 9, "bold")
        ).pack(
            anchor="w",
            pady=(0, 5)
        )

        combo = ttk.Combobox(
            box,
            values=values,
            state="readonly",
            font=("Segoe UI", 10)
        )

        combo.pack(
            fill="x",
            ipady=7
        )

        return combo

    # =====================================================
    # STUDENT DIRECTORY
    # =====================================================

    def build_student_directory(self):

        outer = tk.Frame(
            self.page,
            bg=SURFACE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        outer.pack(
            fill="x",
            padx=28,
            pady=(22, 10)
        )

        # =================================================
        # DIRECTORY HEADER
        # =================================================

        header = tk.Frame(
            outer,
            bg=SURFACE
        )

        header.pack(
            fill="x",
            padx=25,
            pady=(22, 12)
        )

        tk.Label(
            header,
            text="02",
            bg="#111827",
            fg=WHITE,
            font=("Segoe UI", 10, "bold"),
            width=4,
            pady=6
        ).pack(
            side="left"
        )

        title_box = tk.Frame(
            header,
            bg=SURFACE
        )

        title_box.pack(
            side="left",
            padx=12
        )

        tk.Label(
            title_box,
            text="Student Directory",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 19, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            title_box,
            text="Browse and search complete student records",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 10)
        ).pack(
            anchor="w"
        )

        # =================================================
        # SEARCH BAR
        # =================================================

        search = tk.Frame(
            outer,
            bg=SURFACE_2,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        search.pack(
            fill="x",
            padx=25,
            pady=(5, 18)
        )

        self.search_type = ttk.Combobox(
            search,
            values=[
                "name",
                "roll",
                "sid",
                "mobile",
                "father_name"
            ],
            state="readonly",
            width=16,
            font=("Segoe UI", 10)
        )

        self.search_type.current(0)

        self.search_type.pack(
            side="left",
            padx=12,
            pady=12,
            ipady=5
        )

        self.search_var = tk.StringVar()

        self.search_entry = tk.Entry(
            search,
            textvariable=self.search_var,
            bg=WHITE,
            fg=TEXT,
            insertbackground=TEXT,
            relief="flat",
            highlightthickness=1,
            highlightbackground=BORDER,
            font=("Segoe UI", 10)
        )

        self.search_entry.pack(
            side="left",
            fill="x",
            expand=True,
            padx=5,
            ipady=10
        )

        self.search_entry.bind(
            "<Return>",
            lambda event: self.search_student()
        )

        tk.Button(
            search,
            text="SEARCH",
            command=self.search_student,
            bg=PRIMARY,
            fg=WHITE,
            activebackground=PRIMARY_HOVER,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=20,
            pady=10
        ).pack(
            side="left",
            padx=10
        )

        tk.Button(
            search,
            text="CLEAR",
            command=self.clear_search,
            bg="#E5E7EB",
            fg=TEXT_2,
            activebackground="#D1D5DB",
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=15,
            pady=10
        ).pack(
            side="left",
            padx=(0, 12)
        )

        # =================================================
        # LIST
        # =================================================

        self.list_frame = tk.Frame(
            outer,
            bg=SURFACE
        )

        self.list_frame.pack(
            fill="x",
            padx=25,
            pady=(0, 25)
        )

    # =====================================================
    # IMAGE
    # =====================================================

    def select_image(self):

        file_path = filedialog.askopenfilename(
            filetypes=[
                (
                    "Image Files",
                    "*.png *.jpg *.jpeg *.webp"
                )
            ]
        )

        if not file_path:
            return

        os.makedirs(
            "student_photos",
            exist_ok=True
        )

        filename = os.path.basename(
            file_path
        )

        new_path = os.path.join(
            "student_photos",
            filename
        )

        if os.path.abspath(file_path) != os.path.abspath(new_path):

            shutil.copy2(
                file_path,
                new_path
            )

        self.selected_image_path = new_path

        img = Image.open(
            new_path
        )

        img.thumbnail(
            (150, 150)
        )

        photo = ImageTk.PhotoImage(
            img
        )

        self.preview_label.configure(
            image=photo,
            text=""
        )

        self.preview_label.image = photo

        self.update_scroll_region()

    # =====================================================
    # VALIDATION
    # =====================================================

    def validate_fields(self):

        required_fields = {

            "Student ID":
                self.sid.get().strip(),

            "Roll Number":
                self.roll.get().strip(),

            "Student Full Name":
                self.name.get().strip(),

            "Father Name":
                self.father_name.get().strip(),

            "Gender":
                self.gender.get().strip(),

            "College Name":
                self.college.get().strip(),

            "Branch Name":
                self.branch.get().strip(),

            "Semester":
                self.semester.get().strip(),

            "Email ID":
                self.email.get().strip(),

            "Student Mobile Number":
                self.mobile.get().strip()
        }

        missing = []

        for field, value in required_fields.items():

            if not value:

                missing.append(
                    field
                )

        if not self.selected_image_path:

            missing.append(
                "Student Photo"
            )

        if missing:

            messagebox.showwarning(
                "Validation Failed",
                "Please complete these required fields:\n\n"
                + "\n".join(
                    "• " + item
                    for item in missing
                )
            )

            return False

        messagebox.showinfo(
            "AI Validation",
            "All compulsory fields are properly filled."
        )

        return True

    # =====================================================
    # CRUD
    # =====================================================

    def enable_crud(self):

        messagebox.showinfo(
            "CRUD OPERATIONS",
            "Create, Read, Update & Delete Operations "
            "Enabled Successfully."
        )

    # =====================================================
    # ADD STUDENT
    # =====================================================

    def add_student(self):

        if not self.validate_fields():

            return

        sid = self.sid.get().strip()
        roll = self.roll.get().strip()

        if students_collection.find_one({
            "sid": sid
        }):

            messagebox.showerror(
                "Duplicate Student ID",
                "This Student ID already exists."
            )

            return

        if students_collection.find_one({
            "roll": roll
        }):

            messagebox.showerror(
                "Duplicate Roll Number",
                "This Roll Number already exists."
            )

            return

        semester = self.semester.get()

        year = ""

        if semester in ["1", "2"]:
            year = "1st Year"

        elif semester in ["3", "4"]:
            year = "2nd Year"

        elif semester in ["5", "6"]:
            year = "3rd Year"

        elif semester in ["7", "8"]:
            year = "4th Year"

        data = {

            "sid": sid,

            "roll": roll,

            "name":
                self.name.get().strip(),

            "father_name":
                self.father_name.get().strip(),

            "mother_name":
                self.mother_name.get().strip(),

            "gender":
                self.gender.get().strip(),

            "dob":
                self.dob.get().strip(),

            "age":
                self.age.get().strip(),

            "address":
                self.address.get().strip(),

            "marital_status":
                self.marital_status.get().strip(),

            "college":
                self.college.get().strip(),

            "branch":
                self.branch.get().strip(),

            "semester":
                semester,

            "year":
                year,

            "course":
                self.course.get().strip(),

            "admission_date":
                self.admission_date.get().strip(),

            "exit_date":
                self.exit_date.get().strip(),

            "blood_group":
                self.blood_group.get().strip(),

            "email":
                self.email.get().strip(),

            "linkedin":
                self.linkedin.get().strip(),

            "mobile":
                self.mobile.get().strip(),

            "parent_mobile":
                self.parent_mobile.get().strip(),

            "department":
                self.department.get().strip(),

            "photo":
                self.selected_image_path,

            "created_at":
                datetime.now()
        }

        try:

            students_collection.insert_one(
                data
            )

            messagebox.showinfo(
                "Success",
                "Student Added Successfully."
            )

            self.load_students()

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                str(e)
            )

    # =====================================================
    # DELETE
    # =====================================================

    def delete_student(self):

        roll = self.roll.get().strip()

        if not roll:

            messagebox.showwarning(
                "Missing Roll Number",
                "Enter the student's Roll Number."
            )

            return

        student = students_collection.find_one({
            "roll": roll
        })

        if not student:

            messagebox.showwarning(
                "Student Not Found",
                "No student found with this Roll Number."
            )

            return

        confirm = messagebox.askyesno(
            "Confirm Delete",
            f"Delete student '{student.get('name', '')}'?"
        )

        if not confirm:
            return

        students_collection.delete_one({
            "_id": student["_id"]
        })

        messagebox.showinfo(
            "Deleted",
            "Student Deleted Successfully."
        )

        self.load_students()

    # =====================================================
    # SEARCH
    # =====================================================

    def search_student(self):

        keyword = self.search_var.get().strip()

        if not keyword:

            self.load_students()

            return

        search_by = self.search_type.get()

        try:

            students = list(
                students_collection.find({
                    search_by: {
                        "$regex": keyword,
                        "$options": "i"
                    }
                })
            )

            self.display_students(
                students
            )

        except Exception as e:

            messagebox.showerror(
                "Search Error",
                str(e)
            )

    # =====================================================
    # CLEAR SEARCH
    # =====================================================

    def clear_search(self):

        self.search_var.set("")

        self.load_students()

    # =====================================================
    # LOAD
    # =====================================================

    def load_students(self):

        try:

            students = list(
                students_collection.find()
            )

            self.display_students(
                students
            )

        except Exception as e:

            messagebox.showerror(
                "Database Error",
                str(e)
            )

    # =====================================================
    # DISPLAY STUDENTS
    # =====================================================

    def display_students(self, students):

        for widget in self.list_frame.winfo_children():

            widget.destroy()

        # =================================================
        # HEADER / COUNT
        # =================================================

        top = tk.Frame(
            self.list_frame,
            bg=SURFACE
        )

        top.pack(
            fill="x",
            pady=(0, 12)
        )

        tk.Label(
            top,
            text=f"{len(students)} Students",
            bg=SURFACE,
            fg=TEXT,
            font=("Segoe UI", 13, "bold")
        ).pack(
            side="left"
        )

        tk.Label(
            top,
            text="Complete student records",
            bg=SURFACE,
            fg=MUTED,
            font=("Segoe UI", 9)
        ).pack(
            side="left",
            padx=10
        )

        # =================================================
        # EMPTY
        # =================================================

        if not students:

            empty = tk.Frame(
                self.list_frame,
                bg=SURFACE_2,
                highlightbackground=BORDER,
                highlightthickness=1
            )

            empty.pack(
                fill="x",
                pady=10
            )

            tk.Label(
                empty,
                text="No student records found",
                bg=SURFACE_2,
                fg=TEXT,
                font=("Segoe UI", 15, "bold")
            ).pack(
                pady=(30, 4)
            )

            tk.Label(
                empty,
                text="Add a student or change your search.",
                bg=SURFACE_2,
                fg=MUTED,
                font=("Segoe UI", 10)
            ).pack(
                pady=(0, 30)
            )

            self.parent.after(
                50,
                self.update_scroll_region
            )

            return

        # =================================================
        # STUDENT CARDS
        # =================================================

        for student in students:

            self.create_student_card(
                student
            )

        self.parent.after(
            50,
            self.update_scroll_region
        )

    # =====================================================
    # STUDENT CARD
    # =====================================================

    def create_student_card(self, student):

        card = tk.Frame(
            self.list_frame,
            bg=WHITE,
            highlightbackground=BORDER,
            highlightthickness=1
        )

        card.pack(
            fill="x",
            pady=7
        )

        # =================================================
        # PHOTO
        # =================================================

        photo_box = tk.Frame(
            card,
            bg=WHITE
        )

        photo_box.pack(
            side="left",
            padx=18,
            pady=18
        )

        path = student.get(
            "photo"
        )

        if path and os.path.exists(path):

            try:

                img = Image.open(
                    path
                )

                img.thumbnail(
                    (100, 100)
                )

                photo = ImageTk.PhotoImage(
                    img
                )

                label = tk.Label(
                    photo_box,
                    image=photo,
                    bg=WHITE,
                    cursor="hand2"
                )

                label.image = photo

                label.pack()

                label.bind(
                    "<Button-1>",
                    lambda e,
                    p=path:
                    self.show_large_image(p)
                )

            except Exception:

                self.photo_placeholder(
                    photo_box
                )

        else:

            self.photo_placeholder(
                photo_box
            )

        # =================================================
        # MAIN INFO
        # =================================================

        info = tk.Frame(
            card,
            bg=WHITE
        )

        info.pack(
            side="left",
            fill="both",
            expand=True,
            padx=10,
            pady=18
        )

        # Name
        tk.Label(
            info,
            text=student.get("name", ""),
            bg=WHITE,
            fg=TEXT,
            font=("Segoe UI", 15, "bold")
        ).pack(
            anchor="w"
        )

        # Identity
        identity = tk.Frame(
            info,
            bg=WHITE
        )

        identity.pack(
            fill="x",
            pady=(6, 10)
        )

        self.info_badge(
            identity,
            f"SID  {student.get('sid', '')}"
        )

        self.info_badge(
            identity,
            f"ROLL  {student.get('roll', '')}"
        )

        self.info_badge(
            identity,
            f"SEM  {student.get('semester', '')}"
        )

        # Details grid
        details = tk.Frame(
            info,
            bg=WHITE
        )

        details.pack(
            fill="x"
        )

        self.detail(
            details,
            "Father",
            student.get(
                "father_name",
                ""
            ),
            0,
            0
        )

        self.detail(
            details,
            "Branch",
            student.get(
                "branch",
                ""
            ),
            0,
            1
        )

        self.detail(
            details,
            "College",
            student.get(
                "college",
                ""
            ),
            0,
            2
        )

        self.detail(
            details,
            "Mobile",
            student.get(
                "mobile",
                ""
            ),
            1,
            0
        )

        self.detail(
            details,
            "Email",
            student.get(
                "email",
                ""
            ),
            1,
            1
        )

        self.detail(
            details,
            "Department",
            student.get(
                "department",
                ""
            ),
            1,
            2
        )

        self.detail(
            details,
            "Gender",
            student.get(
                "gender",
                ""
            ),
            2,
            0
        )

        self.detail(
            details,
            "DOB",
            student.get(
                "dob",
                ""
            ),
            2,
            1
        )

        self.detail(
            details,
            "Blood Group",
            student.get(
                "blood_group",
                ""
            ),
            2,
            2
        )

        # =================================================
        # RIGHT SIDE
        # =================================================

        right = tk.Frame(
            card,
            bg=WHITE
        )

        right.pack(
            side="right",
            padx=20,
            pady=18,
            anchor="n"
        )

        tk.Label(
            right,
            text=student.get(
                "year",
                ""
            ),
            bg="#F5F3FF",
            fg=PRIMARY,
            font=("Segoe UI", 10, "bold"),
            padx=12,
            pady=7
        ).pack()

        # =================================================
        # ADDRESS
        # =================================================

        address = student.get(
            "address",
            ""
        )

        if address:

            tk.Label(
                info,
                text=f"Address: {address}",
                bg=WHITE,
                fg=MUTED,
                font=("Segoe UI", 9),
                wraplength=850,
                justify="left"
            ).pack(
                anchor="w",
                pady=(12, 0)
            )

    # =====================================================
    # BADGE
    # =====================================================

    def info_badge(
        self,
        parent,
        text
    ):

        tk.Label(
            parent,
            text=text,
            bg="#F3F4F6",
            fg=TEXT_2,
            font=("Segoe UI", 8, "bold"),
            padx=9,
            pady=5
        ).pack(
            side="left",
            padx=(0, 6)
        )

    # =====================================================
    # DETAIL
    # =====================================================

    def detail(
        self,
        parent,
        title,
        value,
        row,
        column
    ):

        box = tk.Frame(
            parent,
            bg=WHITE
        )

        box.grid(
            row=row,
            column=column,
            sticky="w",
            padx=(0, 35),
            pady=4
        )

        tk.Label(
            box,
            text=title.upper(),
            bg=WHITE,
            fg=LIGHT_TEXT,
            font=("Segoe UI", 7, "bold")
        ).pack(
            anchor="w"
        )

        tk.Label(
            box,
            text=value or "—",
            bg=WHITE,
            fg=TEXT_2,
            font=("Segoe UI", 9)
        ).pack(
            anchor="w"
        )

    # =====================================================
    # PHOTO PLACEHOLDER
    # =====================================================

    def photo_placeholder(self, parent):

        tk.Label(
            parent,
            text="NO\nPHOTO",
            bg="#F3F4F6",
            fg=LIGHT_TEXT,
            width=12,
            height=6,
            font=("Segoe UI", 8, "bold")
        ).pack()

    # =====================================================
    # LARGE PHOTO
    # =====================================================

    def show_large_image(self, path):

        if not os.path.exists(path):

            messagebox.showerror(
                "Image Error",
                "Student photo could not be found."
            )

            return

        top = tk.Toplevel(
            self.parent
        )

        top.title(
            "Student Photo Preview"
        )

        top.configure(
            bg="#111827"
        )

        top.geometry(
            "540x620"
        )

        img = Image.open(
            path
        )

        img.thumbnail(
            (480, 500)
        )

        photo = ImageTk.PhotoImage(
            img
        )

        label = tk.Label(
            top,
            image=photo,
            bg="#111827"
        )

        label.image = photo

        label.pack(
            padx=20,
            pady=20
        )

        tk.Button(
            top,
            text="CLOSE",
            command=top.destroy,
            bg=PRIMARY,
            fg=WHITE,
            relief="flat",
            cursor="hand2",
            font=("Segoe UI", 10, "bold"),
            padx=30,
            pady=9
        ).pack()

    # =====================================================
    # DESTROY SCROLL BINDINGS
    # =====================================================

    def destroy(self):

        self.canvas.unbind_all(
            "<MouseWheel>"
        )

        self.canvas.unbind_all(
            "<Button-4>"
        )

        self.canvas.unbind_all(
            "<Button-5>"
        )

        self.canvas.unbind_all(
            "<Prior>"
        )

        self.canvas.unbind_all(
            "<Next>"
        )

        self.canvas.unbind_all(
            "<Home>"
        )

        self.canvas.unbind_all(
            "<End>"
        )


# =========================================================
# FUNCTION CALLED FROM MAIN.PY
# =========================================================

def open_admin_panel(
    parent,
    session=None
):

    StudentManagementApp(
        parent,
        session
    )


# =========================================================
# DIRECT RUN
# =========================================================

if __name__ == "__main__":

    root = tk.Tk()

    root.title(
        "Student Management System"
    )

    root.geometry(
        "1500x900"
    )

    root.minsize(
        1000,
        650
    )

    StudentManagementApp(
        root
    )

    root.mainloop()