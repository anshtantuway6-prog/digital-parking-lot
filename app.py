# digital-parking-lot
import streamlit as st, mysql.connector, pandas as pd, matplotlib.pyplot as plt
import hashlib, secrets, math, os
from datetime import datetime, timedelta
import streamlit.components.v1 as components

try:
    DB = dict(st.secrets["mysql"])
except Exception:
    DB = dict(host="localhost", user="root", password="", database="digital_parking")RATE = {"Car": 20, "Bike": 10, "Scooty": 10}          # rupees per hour
ICON = {"Car": "🚗", "Bike": "🏍️", "Scooty": "🛵"}
BRANDS = {  # brand name -> logo name on simpleicons.org ("" = no logo, emoji is shown)
    "Car": {"Rolls-Royce": "rollsroyce", "BMW": "bmw", "Audi": "audi", "Mercedes": "mercedes",
            "Tesla": "tesla", "Toyota": "toyota", "Honda": "honda", "Hyundai": "hyundai",
            "Kia": "kia", "Tata": "tata", "Mahindra": "mahindra", "Ford": "ford",
            "Volkswagen": "volkswagen", "Ferrari": "ferrari", "Lamborghini": "lamborghini",
            "Porsche": "porsche", "Suzuki": "suzuki", "Other": ""},
    "Bike": {"Royal Enfield": "royalenfield", "Yamaha": "yamaha", "Kawasaki": "kawasaki",
             "Ducati": "ducati", "Honda": "honda", "Bajaj": "bajajauto", "TVS": "tvsmotor",
             "Hero": "heromotocorp", "Suzuki": "suzuki", "Other": ""},
    "Scooty": {"Honda": "honda", "TVS": "tvsmotor", "Suzuki": "suzuki", "Yamaha": "yamaha",
               "Hero": "heromotocorp", "Other": ""}}

st.set_page_config(page_title="Digital Parking Lot", page_icon="🅿️", layout="wide")
st.markdown("""<style>
.stApp{font-family:'Segoe UI',Arial,sans-serif;font-size:14px}
h1,h2,h3{color:#FFC107!important}
div[role=radiogroup]{justify-content:center;gap:6px;flex-wrap:wrap}
div[role=radiogroup] label{background:#1a1a1a;border:1px solid #333;border-radius:6px;padding:3px 12px}
.stButton>button,.stFormSubmitButton>button,.stDownloadButton>button{background:#FFC107;color:#000;font-weight:600;border:0}
.grid{display:grid;grid-template-columns:repeat(8,1fr);gap:8px}
.slot{background:#161616;border:1px solid #333;border-radius:8px;text-align:center;padding:8px 2px;font-size:20px;min-height:62px}
.slot small{display:block;font-size:10px;color:#aaa}
.busy{border-color:#FFC107}
.hero{text-align:center}
</style>""", unsafe_allow_html=True)

LOGO = """<svg width="90" height="90" viewBox="0 0 100 100"><rect width="100" height="100" rx="22" fill="#FFC107"/>
<path d="M34 78V24h18c13 0 20 7 20 17s-7 17-20 17H44" fill="none" stroke="#0b0b0b" stroke-width="10" stroke-linecap="round"/></svg>"""


# ---------- database helpers ----------
def run(sql, args=(), fetch=True):
    con = mysql.connector.connect(**DB)
    cur = con.cursor()
    cur.execute(sql, args)
    out = None
    if fetch:
        out = pd.DataFrame(cur.fetchall(), columns=[c[0] for c in cur.description])
    else:
        con.commit()
    cur.close()
    con.close()
    return out


def hp(pw, salt):
    return hashlib.pbkdf2_hmac("sha256", pw.encode(), bytes.fromhex(salt), 200000).hex()


def sh(t):
    return hashlib.sha256(t.encode()).hexdigest()


def set_cookie(val, days):
    components.html(f"<script>window.parent.document.cookie='dpl_trust={val}; max-age={days*86400}; path=/; SameSite=Lax';</script>", height=0)


def is_trusted():
    t = st.context.cookies.get("dpl_trust")
    if not t:
        return False
    return not run("SELECT 1 FROM trusted_devices WHERE token_hash=%s AND expires>%s", (sh(t), datetime.now())).empty


def newfig():
    fig, ax = plt.subplots(figsize=(4.2, 3))
    fig.patch.set_facecolor("#161616")
    ax.set_facecolor("#161616")
    return fig, ax


def show(fig, ax, title):
    ax.set_title(title, color="#FFC107", fontsize=10)
    ax.tick_params(colors="#ddd", labelsize=8)
    ax.xaxis.label.set_color("#ddd")
    for s in ax.spines.values():
        s.set_color("#444")
    st.pyplot(fig)
    plt.close(fig)


# ---------- pages ----------
def home():
    st.markdown(f'<div class="hero"><h2>Namaste 🙏, Welcome to Digital Parking Lot</h2>{LOGO}'
                '<h3 style="margin-top:6px">Smart. Secure. Efficient.</h3></div>', unsafe_allow_html=True)
    s = run("SELECT * FROM slots")
    used = int(s.is_occupied.sum())
    a, b, c = st.columns(3)
    a.metric("Total slots", len(s))
    b.metric("Occupied", used)
    c.metric("Free", len(s) - used)


def dashboard():
    st.header("Dashboard")
    b = run("SELECT s.slot_id, r.vehicle_no, r.vehicle_type, r.brand FROM slots s "
            "LEFT JOIN records r ON r.slot_id = s.slot_id AND r.exit_time IS NULL ORDER BY s.slot_id")
    cells = ""
    for _, r in b.iterrows():
        if pd.isna(r.vehicle_no):
            cells += f'<div class="slot">⬜<small>Slot {r.slot_id}</small></div>'
        else:
            slug = BRANDS[r.vehicle_type].get(r.brand, "")
            icon = f'<img src="https://cdn.simpleicons.org/{slug}/FFC107" width="28" height="28">' if slug else ICON[r.vehicle_type]
            cells += f'<div class="slot busy">{icon}<small>{r.vehicle_no}</small></div>'
    st.markdown(f'<div class="grid">{cells}</div>', unsafe_allow_html=True)

    st.subheader("Vehicle info")
    act = run("SELECT * FROM records WHERE exit_time IS NULL ORDER BY slot_id")
    if act.empty:
        st.info("No vehicle is parked right now.")
    else:
        pick = st.selectbox("Select a parked vehicle", act.vehicle_no)
        r = act[act.vehicle_no == pick].iloc[0]
        c1, c2 = st.columns([2, 1])
        c1.write(f"**Owner:** {r.owner}  \n**Type:** {ICON[r.vehicle_type]} {r.vehicle_type} ({r.brand})  \n"
                 f"**Destination:** {r.destination}  \n**Slot:** {r.slot_id}  \n**Entry:** {r.entry_time}  \n**Exit:** still parked")
        if r.photo_path and os.path.exists(r.photo_path):
            c2.image(r.photo_path, width=200)

    st.subheader("Analytics")
    df = run("SELECT * FROM records")
    if df.empty:
        st.info("Charts will appear after the first vehicle entry.")
        return
    df["fee"] = pd.to_numeric(df["fee"])
    df["entry_time"] = pd.to_datetime(df["entry_time"])
    done = df[df.fee.notna()].copy()
    used = int((b.vehicle_no.notna()).sum())
    c1, c2, c3 = st.columns(3)
    with c1:
        fig, ax = newfig()
        ax.pie([len(b) - used, used], labels=["Free", "Occupied"], autopct="%1.0f%%",
               colors=["#555", "#FFC107"], textprops={"color": "#fff"})
        show(fig, ax, "Occupancy %")
    with c2:
        fig, ax = newfig()
        df.vehicle_type.value_counts().plot.bar(ax=ax, color="#FFC107")
        show(fig, ax, "Vehicle types")
    with c3:
        fig, ax = newfig()
        df.groupby(df.entry_time.dt.hour).size().plot(ax=ax, color="#FFC107", marker="o")
        ax.set_xlabel("Hour of day")
        show(fig, ax, "Peak hours")
    if not done.empty:
        c4, c5 = st.columns(2)
        with c4:
            fig, ax = newfig()
            done.groupby("vehicle_type").fee.sum().plot.bar(ax=ax, color="#FFC107")
            show(fig, ax, "Revenue by vehicle type (Rs)")
        with c5:
            fig, ax = newfig()
            done.groupby(pd.to_datetime(done.exit_time).dt.date).fee.sum().plot(ax=ax, color="#FFC107", marker="o")
            show(fig, ax, "Revenue trend (Rs)")
    st.download_button("⬇ Export report (CSV)", df.to_csv(index=False), "parking_report.csv")


def entry():
    st.header("Vehicle Entry")
    vt = st.radio("Vehicle type", list(RATE), horizontal=True, format_func=lambda v: f"{ICON[v]} {v}")
    with st.form("entry", clear_on_submit=True):
        owner = st.text_input("Owner name")
        vno = st.text_input("Vehicle number (e.g. MP04AB1234)").strip().upper()
        brand = st.selectbox("Brand (its logo shows on the slot)", list(BRANDS[vt]))
        dest = st.text_input("Destination")
        photo = st.camera_input("Vehicle photo")
        go = st.form_submit_button("Park vehicle")
    if not go:
        return
    if not (owner and vno and dest):
        st.error("Please fill owner name, vehicle number and destination.")
    elif not run("SELECT 1 FROM records WHERE vehicle_no=%s AND exit_time IS NULL", (vno,)).empty:
        st.error("This vehicle is already parked.")
    else:
        free = run("SELECT slot_id FROM slots WHERE is_occupied=0 ORDER BY slot_id LIMIT 1")
        if free.empty:
            st.error("Parking is full!")
            return
        slot, path = int(free.slot_id[0]), ""
        if photo:
            os.makedirs("photos", exist_ok=True)
            path = f"photos/{vno}_{datetime.now():%Y%m%d%H%M%S}.jpg"
            open(path, "wb").write(photo.getvalue())
        run("INSERT INTO records (owner, vehicle_no, vehicle_type, brand, destination, photo_path, slot_id, entry_time) "
            "VALUES (%s,%s,%s,%s,%s,%s,%s,%s)", (owner, vno, vt, brand, dest, path, slot, datetime.now()), False)
        run("UPDATE slots SET is_occupied=1 WHERE slot_id=%s", (slot,), False)
        st.success(f"✅ {vno} parked at Slot {slot}")


def exit_page():
    st.header("Vehicle Exit")
    with st.form("exit"):
        vno = st.text_input("Search by vehicle number").strip().upper()
        go = st.form_submit_button("Search & exit")
    if not go:
        return
    d = run("SELECT * FROM records WHERE vehicle_no=%s AND exit_time IS NULL", (vno,))
    if d.empty:
        st.error("No parked vehicle found with this number.")
        return
    r, now = d.iloc[0], datetime.now()
    hrs = max(1, math.ceil((now - r.entry_time).total_seconds() / 3600))
    fee = hrs * RATE[r.vehicle_type]
    run("UPDATE records SET exit_time=%s, fee=%s WHERE id=%s", (now, fee, int(r.id)), False)
    run("UPDATE slots SET is_occupied=0 WHERE slot_id=%s", (int(r.slot_id),), False)
    st.success(f"✅ {vno} exited. Slot {r.slot_id} is free.")
    st.write(f"**Owner:** {r.owner}  \n**Time parked:** {hrs} hour(s) × Rs {RATE[r.vehicle_type]}  \n## Total fee: Rs {fee}")


def admin():
    st.header("Admin")
    if not st.session_state.get("admin") and is_trusted():
        st.session_state.admin = True
    if not st.session_state.get("admin"):
        with st.form("login"):
            u = st.text_input("Username")
            p = st.text_input("Password", type="password")
            trust = st.checkbox("Trust this device (no password for 30 days)")
            go = st.form_submit_button("Login")
        if go:
            d = run("SELECT pw_hash, salt FROM admin WHERE username=%s", (u,))
            if not d.empty and secrets.compare_digest(hp(p, d.salt[0]), d.pw_hash[0]):
                st.session_state.admin = True
                if trust:
                    tok = secrets.token_urlsafe(32)
                    run("INSERT INTO trusted_devices VALUES (%s,%s)", (sh(tok), datetime.now() + timedelta(days=30)), False)
                    set_cookie(tok, 30)
                st.success("✅ Login Successful! Welcome Admin")
            else:
                st.error("❌ Incorrect Password")
    if not st.session_state.get("admin"):
        return

    q = st.text_input("Search by vehicle number / owner")
    df = run("SELECT * FROM records ORDER BY id DESC")
    view = df
    if q and not df.empty:
        view = df[df.vehicle_no.str.contains(q.upper(), na=False) | df.owner.str.contains(q, case=False, na=False)]
    st.dataframe(view, use_container_width=True)
    st.download_button("⬇ Download full parking history (CSV)", df.to_csv(index=False), "parking_history.csv")

    rid = st.number_input("Record ID to delete", min_value=0, step=1)
    if st.button("🗑 Delete record") and rid:
        r = run("SELECT slot_id, exit_time FROM records WHERE id=%s", (int(rid),))
        if r.empty:
            st.error("No record with that ID.")
        else:
            if pd.isna(r.exit_time[0]):
                run("UPDATE slots SET is_occupied=0 WHERE slot_id=%s", (int(r.slot_id[0]),), False)
            run("DELETE FROM records WHERE id=%s", (int(rid),), False)
            st.success("Record deleted.")
    if st.button("Logout"):
        t = st.context.cookies.get("dpl_trust")
        if t:
            run("DELETE FROM trusted_devices WHERE token_hash=%s", (sh(t),), False)
        set_cookie("", 0)
        st.session_state.admin = False
        st.info("Logged out. This device is no longer trusted.")


def contact():
    st.header("Contact")
    with st.form("contact", clear_on_submit=True):
        n, e, m = st.text_input("Name"), st.text_input("Email"), st.text_area("Message")
        if st.form_submit_button("Send") and n and m:
            run("INSERT INTO messages (name,email,message,created) VALUES (%s,%s,%s,%s)", (n, e, m, datetime.now()), False)
            st.success("Message sent. Thank you!")


TEXT = {
    "About": "**Digital Parking Lot** is a parking management system that records vehicles, assigns slots, "
             "calculates fees and shows live analytics.\n\n**Tech stack:** MySQL, Pandas, Matplotlib, Streamlit.\n\n"
             "**Purpose:** Digital parking management.",
    "FAQ": "**How does entry/exit work?** Fill the entry form and a free slot is assigned. At exit, search the vehicle "
           "number; the fee is calculated and the slot is freed.\n\n**How are photos stored?** Saved in the `photos` "
           "folder; only the file path is saved in MySQL.\n\n**How to delete records?** Only the admin can delete "
           "records, from the Admin page.\n\n**How is revenue calculated?** Hours parked (rounded up, minimum 1) × "
           "hourly rate: Car Rs 20, Bike Rs 10, Scooty Rs 10.",
    "Privacy": "Vehicle and owner data is stored until the admin deletes it manually. Data is used only for parking "
               "management and is not shared with anyone.",
    "Terms": "This is an academic project made for demo purposes. Do not enter real sensitive information.",
}
PAGES = {"Home": home, "Dashboard": dashboard, "Vehicle Entry": entry, "Vehicle Exit": exit_page, "Admin": admin,
         "Contact": contact, "About": lambda: (st.header("About"), st.markdown(TEXT["About"])),
         "FAQ": lambda: (st.header("FAQ"), st.markdown(TEXT["FAQ"])),
         "Privacy": lambda: (st.header("Privacy Policy"), st.markdown(TEXT["Privacy"])),
         "Terms": lambda: (st.header("Terms of Use"), st.markdown(TEXT["Terms"]))}

page = st.radio("nav", list(PAGES), horizontal=True, label_visibility="collapsed")
PAGES[page]()
st.markdown('<hr><p style="text-align:center;color:#888;font-size:12px">About | Privacy | Terms &nbsp;·&nbsp; '
            'Developed by [Your Name]</p>', unsafe_allow_html=True)
