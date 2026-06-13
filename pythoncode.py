import streamlit as st
import mysql.connector
import pandas as pd
import cv2
import numpy as np
from PIL import Image

# ------------------------------------------------
# Database connection
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
# Decode QR code from image
# ------------------------------------------------
def decode_qr_code(uploaded_image):
    image = Image.open(uploaded_image).convert("RGB")
    image_np = np.array(image)

    detector = cv2.QRCodeDetector()
    qr_data, bbox, straight_qrcode = detector.detectAndDecode(image_np)

    return qr_data


# ------------------------------------------------
# Parse QR code data
# Format: EMPID-FIRSTNAME-LASTNAME
# Example: 101-AMIT-SHARMA
# ------------------------------------------------
def parse_qr_data(qr_data):
    parts = qr_data.strip().split("-")

    if len(parts) != 3:
        raise ValueError("Invalid QR format. Expected format: EMPID-FIRSTNAME-LASTNAME")

    emp_id = int(parts[0])
    first_name = parts[1].strip()
    last_name = parts[2].strip()

    full_name = f"{first_name} {last_name}"

    return emp_id, full_name


# ------------------------------------------------
# Insert login record into MySQL cloud table
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
# Fetch login records
# ------------------------------------------------
def fetch_login_records():
    conn_obj = get_connection()

    query = """
    SELECT *
    FROM employee_login_details
    ORDER BY login_datetime DESC
    """

    df = pd.read_sql(query, conn_obj)

    conn_obj.close()

    return df


# ------------------------------------------------
# Streamlit Frontend
# ------------------------------------------------
st.set_page_config(page_title="QR Attendance App", layout="wide")

st.title("QR Code Employee Login System")
st.write("Scan employee QR code and insert login details into Railway MySQL cloud database.")

menu = st.sidebar.radio(
    "Select Option",
    ["Scan QR Code", "View Login Records"]
)

if menu == "Scan QR Code":

    st.subheader("Scan Employee QR Code")

    st.info("QR format should be: EMPID-FIRSTNAME-LASTNAME")
    st.write("Example: `101-AMIT-SHARMA`")

    camera_image = st.camera_input("Open camera and scan QR code")

    if camera_image is not None:

        try:
            qr_data = decode_qr_code(camera_image)

            if qr_data:
                st.success("QR Code scanned successfully.")
                st.write("Scanned QR Data:", qr_data)

                emp_id, full_name = parse_qr_data(qr_data)

                st.write("Employee ID:", emp_id)
                st.write("Full Name:", full_name)

                if st.button("Submit Login Record"):
                    insert_login_record(emp_id, full_name)
                    st.success("Employee login record inserted successfully into cloud MySQL.")

            else:
                st.error("No QR code detected. Please try again with a clearer image.")

        except ValueError as ve:
            st.error(str(ve))

        except mysql.connector.Error as db_error:
            st.error("Database error occurred.")
            st.write(db_error)

        except Exception as e:
            st.error("Something went wrong.")
            st.write(e)


elif menu == "View Login Records":

    st.subheader("Employee Login Records")

    try:
        df = fetch_login_records()
        st.dataframe(df, use_container_width=True)

    except mysql.connector.Error as db_error:
        st.error("Database error occurred.")
        st.write(db_error)

    except Exception as e:
        st.error("Something went wrong.")
        st.write(e)