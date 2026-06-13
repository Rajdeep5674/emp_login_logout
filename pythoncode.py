import streamlit as st
import mysql.connector
import pandas as pd
import cv2
import numpy as np
from PIL import Image


# ------------------------------------------------
# Streamlit Page Config
# ------------------------------------------------
st.set_page_config(
    page_title="QR Employee Login System",
    layout="wide"
)


# ------------------------------------------------
# Database Connection
# ------------------------------------------------
def get_connection():
    conn_obj = mysql.connector.connect(
        host=st.secrets["DB_HOST"],
        port=int(st.secrets["DB_PORT"]),
        user=st.secrets["DB_USER"],
        password=st.secrets["DB_PASSWORD"],
        database=st.secrets["DB_NAME"]
    )
    return conn_obj


# ------------------------------------------------
# Decode QR Code Using OpenCV
# ------------------------------------------------
def decode_qr_code(uploaded_image):
    """
    This function receives image from Streamlit camera_input
    and tries multiple OpenCV techniques to decode QR code.
    """

    image = Image.open(uploaded_image).convert("RGB")
    image_np = np.array(image)

    detector = cv2.QRCodeDetector()

    # Attempt 1: Direct RGB image scan
    qr_data, bbox, straight_qrcode = detector.detectAndDecode(image_np)
    if qr_data:
        return qr_data.strip()

    # Attempt 2: Convert RGB to Grayscale
    gray = cv2.cvtColor(image_np, cv2.COLOR_RGB2GRAY)

    qr_data, bbox, straight_qrcode = detector.detectAndDecode(gray)
    if qr_data:
        return qr_data.strip()

    # Attempt 3: Resize image
    resized = cv2.resize(
        gray,
        None,
        fx=2,
        fy=2,
        interpolation=cv2.INTER_CUBIC
    )

    qr_data, bbox, straight_qrcode = detector.detectAndDecode(resized)
    if qr_data:
        return qr_data.strip()

    # Attempt 4: Gaussian Blur + Threshold
    blurred = cv2.GaussianBlur(resized, (5, 5), 0)

    _, threshold_img = cv2.threshold(
        blurred,
        0,
        255,
        cv2.THRESH_BINARY + cv2.THRESH_OTSU
    )

    qr_data, bbox, straight_qrcode = detector.detectAndDecode(threshold_img)
    if qr_data:
        return qr_data.strip()

    # Attempt 5: Adaptive Threshold
    adaptive_threshold = cv2.adaptiveThreshold(
        resized,
        255,
        cv2.ADAPTIVE_THRESH_GAUSSIAN_C,
        cv2.THRESH_BINARY,
        31,
        2
    )

    qr_data, bbox, straight_qrcode = detector.detectAndDecode(adaptive_threshold)
    if qr_data:
        return qr_data.strip()

    return ""


# ------------------------------------------------
# Parse QR Data
# Expected Format: EMPID-FIRSTNAME-LASTNAME
# Example: 101-AMIT-SHARMA
# ------------------------------------------------
def parse_qr_data(qr_data):
    if not qr_data:
        raise ValueError("QR data is empty.")

    parts = qr_data.strip().split("-")

    if len(parts) != 3:
        raise ValueError(
            "Invalid QR format. Expected format: EMPID-FIRSTNAME-LASTNAME"
        )

    emp_id_text = parts[0].strip()
    first_name = parts[1].strip()
    last_name = parts[2].strip()

    if not emp_id_text.isdigit():
        raise ValueError("Employee ID must be numeric.")

    emp_id = int(emp_id_text)
    full_name = f"{first_name} {last_name}"

    return emp_id, full_name


# ------------------------------------------------
# Insert Login Record into MySQL Cloud Table
# ------------------------------------------------
def insert_login_record(emp_id, full_name):
    conn_obj = get_connection()
    cur_obj = conn_obj.cursor()

    query = """
    INSERT INTO employee_login_details
    (emp_id, full_name, login_datetime)
    VALUES (%s, %s, NOW())
    """

    data = (emp_id, full_name)

    cur_obj.execute(query, data)
    conn_obj.commit()

    cur_obj.close()
    conn_obj.close()


# ------------------------------------------------
# Fetch Login Records
# ------------------------------------------------
def fetch_login_records():
    conn_obj = get_connection()

    query = """
    SELECT 
        sl_no,
        emp_id,
        full_name,
        login_datetime
    FROM employee_login_details
    ORDER BY login_datetime DESC
    """

    df = pd.read_sql(query, conn_obj)

    conn_obj.close()

    return df


# ------------------------------------------------
# Main Streamlit App
# ------------------------------------------------
st.title("QR Code Employee Login System")

st.write(
    "Scan employee QR code and insert login details into Railway MySQL cloud database."
)

menu = st.sidebar.radio(
    "Select Option",
    ["Scan QR Code", "View Login Records"]
)


# ------------------------------------------------
# Scan QR Code Page
# ------------------------------------------------
if menu == "Scan QR Code":

    st.subheader("Scan Employee QR Code")

    st.info("QR format should be: EMPID-FIRSTNAME-LASTNAME")
    st.write("Example: `101-AMIT-SHARMA`")

    input_method = st.radio(
        "Choose input method",
        ["Scan QR using Camera", "Enter QR Data Manually"]
    )

    qr_data = ""

    # --------------------------------------------
    # Camera QR Scan
    # --------------------------------------------
    if input_method == "Scan QR using Camera":

        camera_image = st.camera_input("Open camera and scan QR code")

        if camera_image is not None:

            try:
                qr_data = decode_qr_code(camera_image)

                if qr_data:
                    st.success("QR Code scanned successfully.")
                    st.write("Scanned QR Data:", qr_data)

                else:
                    st.error(
                        "No QR code detected. Please try again with a clearer image."
                    )
                    st.warning(
                        "Tip: Bring camera closer, avoid glare, or use manual entry."
                    )

            except Exception as e:
                st.error("QR scanning failed.")
                st.write(e)

    # --------------------------------------------
    # Manual QR Data Entry
    # --------------------------------------------
    else:
        qr_data = st.text_input(
            "Enter QR Data",
            placeholder="Example: 101-AMIT-SHARMA"
        )

    # --------------------------------------------
    # Parse and Insert Data
    # --------------------------------------------
    if qr_data:

        try:
            emp_id, full_name = parse_qr_data(qr_data)

            st.write("Employee ID:", emp_id)
            st.write("Full Name:", full_name)

            if st.button("Submit Login Record"):
                insert_login_record(emp_id, full_name)
                st.success(
                    "Employee login record inserted successfully into cloud MySQL."
                )

        except ValueError as ve:
            st.error(str(ve))

        except mysql.connector.Error as db_error:
            st.error("Database error occurred.")
            st.write(db_error)

        except Exception as e:
            st.error("Something went wrong.")
            st.write(e)


# ------------------------------------------------
# View Records Page
# ------------------------------------------------
elif menu == "View Login Records":

    st.subheader("Employee Login Records")

    try:
        df = fetch_login_records()

        if df.empty:
            st.warning("No login records found.")
        else:
            st.dataframe(df, use_container_width=True)

    except mysql.connector.Error as db_error:
        st.error("Database error occurred.")
        st.write(db_error)

    except Exception as e:
        st.error("Something went wrong.")
        st.write(e)
