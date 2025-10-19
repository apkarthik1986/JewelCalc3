"""
JewelCalc - Jewellery Billing & Customer Management System
A professional multi-user Streamlit application for jewellery shops
"""
import streamlit as st
import pandas as pd
from database import Database
from utils import format_currency, generate_invoice_number, generate_account_number, validate_phone, calculate_item_totals
from pdf_generator import create_invoice_pdf, get_pdf_download_link, create_thermal_invoice_pdf
from auth import show_login_page, show_user_menu, require_auth, require_admin
import os
import hashlib
import platform
import streamlit.components.v1 as components


# Page configuration
st.set_page_config(
    page_title="JewelCalc",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom CSS
# Important:
# - Keep Streamlit toolbar/header and collapsedControl intact so the native sidebar << / >> controls remain visible and functional.
# - Hide only the top-right toolbar action buttons (Share / Star / Edit / GitHub icon) using header-scoped selectors.
# - Continue hiding the three-dot main menu (#MainMenu) as requested.
st.markdown("""
    <style>
    /* --- Keep native toolbar/header & collapsed control --- */
    /* Do NOT hide [data-testid="stToolbar"], header, or [data-testid="collapsedControl"] */

    /* --- Hide specific top-right header toolbar actions (Share / Star / Edit / GitHub) --- */
    /* Scope selectors to 'header' to avoid touching other page elements */
    header .stToolbarActions,
    header [data-testid="stToolbarActions"],
    header .stToolbarActionButton,
    header [data-testid="stToolbarActionButton"] {
        display: none !important;
        pointer-events: none !important;
        visibility: hidden !important;
        height: 0 !important;
        width: 0 !important;
        overflow: hidden !important;
    }

    /* Keep the three-dot main menu hidden as requested */
    #MainMenu { visibility: hidden !important; pointer-events: none !important; }

    /*
      NOTE: We intentionally avoid selectors like [data-testid="stToolbar"] or
      [data-testid="collapsedControl"] so the sidebar collapse/open arrows (<< / >>)
      remain visible and functional.
    */

    /* --- App styling preserved below --- */

    /* Remove top padding to prevent blocking navigation buttons */
    .block-container {
        padding-top: 1rem;
        max-width: 1200px;
    }
    
    /* Custom header */
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 25px;
        border-radius: 15px;
        margin-bottom: 25px;
        text-align: center;
        box-shadow: 0 4px 15px rgba(0,0,0,0.2);
    }
    .main-header h1 {
        color: white;
        margin: 0;
        font-size: 2.5rem;
        text-shadow: 2px 2px 4px rgba(0,0,0,0.3);
        font-weight: 700;
    }
    
    /* Cards */
    .card {
        background: white;
        padding: 20px;
        border-radius: 10px;
        box-shadow: 0 2px 8px rgba(0,0,0,0.1);
        margin-bottom: 20px;
    }
    
    /* Mobile responsive */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 1rem;
            padding-right: 1rem;
            padding-top: 1rem;
        }
        .main-header {
            padding: 15px;
            margin-bottom: 15px;
        }
        .main-header h1 {
            font-size: 1.8rem;
        }
        /* Make buttons stack on mobile */
        .row-widget.stButton {
            width: 100%;
        }
        /* Better mobile forms */
        .stTextInput > div > div > input,
        .stNumberInput > div > div > input,
        .stSelectbox > div > div > select {
            font-size: 16px !important;
        }
    }
    
    /* Success/Error styling */
    .stSuccess {
        background-color: #d4edda;
        border-color: #c3e6cb;
        color: #155724;
        border-radius: 5px;
        padding: 10px;
    }
    
    .stError {
        background-color: #f8d7da;
        border-color: #f5c6cb;
        color: #721c24;
        border-radius: 5px;
        padding: 10px;
    }
    
    .stWarning {
        background-color: #fff3cd;
        border-color: #ffeeba;
        color: #856404;
        border-radius: 5px;
        padding: 10px;
    }
    
    .stInfo {
        background-color: #d1ecf1;
        border-color: #bee5eb;
        color: #0c5460;
        border-radius: 5px;
        padding: 10px;
    }
    
    /* Better form styling */
    .stTextInput > div > div > input,
    .stNumberInput > div > div > input,
    .stTextArea > div > div > textarea {
        border-radius: 8px;
        border: 2px solid #e0e0e0;
        transition: border-color 0.3s;
    }
    
    .stTextInput > div > div > input:focus,
    .stNumberInput > div > div > input:focus,
    .stTextArea > div > div > textarea:focus {
        border-color: #667eea;
        box-shadow: 0 0 0 2px rgba(102, 126, 234, 0.1);
    }
    
    /* Tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background-color: #f5f5f5;
        padding: 10px;
        border-radius: 10px;
    }
    .stTabs [data-baseweb="tab"] {
        height: 50px;
        padding-left: 20px;
        padding-right: 20px;
        border-radius: 8px;
        background-color: white;
        font-weight: 600;
    }
    .stTabs [data-baseweb="tab"][aria-selected="true"] {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
    }
    
    /* Button styling */
    .stButton > button {
        border-radius: 8px;
        font-weight: 600;
        transition: all 0.3s;
    }
    
    .stButton > button:hover {
        transform: translateY(-2px);
        box-shadow: 0 4px 8px rgba(0,0,0,0.15);
    }
    
    /* Sidebar styling */
    [data-testid="stSidebar"] {
        background: linear-gradient(180deg, #f8f9fa 0%, #e9ecef 100%);
    }
    
    /* Dataframe styling */
    .dataframe {
        border-radius: 8px;
        overflow: hidden;
    }
    
    /* Expander styling */
    .streamlit-expanderHeader {
        border-radius: 8px;
        background-color: #f8f9fa;
        font-weight: 600;
    }
    </style>
""", unsafe_allow_html=True)


def get_device_id():
    """Generate a unique device identifier based on system information"""
    try:
        # Get system information to create a unique device ID
        system_info = f"{platform.node()}-{platform.system()}-{platform.machine()}"
        # Create a hash of the system info (MD5 is sufficient for non-cryptographic device ID)
        device_hash = hashlib.md5(system_info.encode()).hexdigest()[:8]
        return device_hash
    except Exception:
        # Fallback to a simple identifier if system info is unavailable
        return "default"


# Initialize session state
def init_session_state():
    """Initialize session state variables"""
    # Authentication state
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    
    if 'db_path' not in st.session_state:
        # Use a central auth database by default
        st.session_state.db_path = "jewelcalc_auth.db"
    
    if 'metal_settings' not in st.session_state:
        st.session_state.metal_settings = {
            'Gold 24K': {'rate': 6500.0, 'wastage': 5.0, 'making': 10.0},
            'Gold 22K': {'rate': 6000.0, 'wastage': 6.0, 'making': 12.0},
            'Gold 18K': {'rate': 5500.0, 'wastage': 7.0, 'making': 14.0},
            'Silver': {'rate': 75.0, 'wastage': 3.0, 'making': 8.0}
        }
    
    if 'cgst' not in st.session_state:
        st.session_state.cgst = 1.5
    
    if 'sgst' not in st.session_state:
        st.session_state.sgst = 1.5
    
    if 'current_invoice_items' not in st.session_state:
        st.session_state.current_invoice_items = []
    
    if 'selected_customer_id' not in st.session_state:
        st.session_state.selected_customer_id = None
    
    if 'discount' not in st.session_state:
        st.session_state.discount = 0.0


init_session_state()

# Initialize database (for authentication initially)
auth_db = Database("jewelcalc_auth.db")
auth_db.create_admin_if_not_exists()

# Check authentication
if not require_auth(auth_db):
    st.stop()

# After login, initialize user's database
db = Database(st.session_state.db_path)

# Header
st.markdown('<div class="main-header"><h1>💎 JewelCalc</h1></div>', unsafe_allow_html=True)

# Show user menu
show_user_menu()

# Main tabs - now including Database and Admin tabs
if require_admin():
    tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
        "⚙️ Settings", "👥 Customers", "📝 Create Invoice", 
        "📋 View Invoices", "🗄️ Database", "🔐 Admin"
    ])
else:
    tab1, tab2, tab3, tab4, tab5 = st.tabs([
        "⚙️ Settings", "👥 Customers", "📝 Create Invoice", 
        "📋 View Invoices", "🗄️ Database"
    ])

# ============================================================================
# TAB 1: SETTINGS
# ============================================================================
with tab1:
    st.markdown("### ⚙️ Base Settings")
    
    st.markdown("#### Metal Settings")
    
    # Edit metal settings
    metals_data = []
    for metal, settings in st.session_state.metal_settings.items():
        metals_data.append({
            'Metal': metal,
            'Rate (per gram)': settings['rate'],
            'Wastage %': settings['wastage'],
            'Making %': settings['making']
        })
    
    df_metals = pd.DataFrame(metals_data)
    edited_metals = st.data_editor(
        df_metals,
        num_rows="dynamic",
        width='stretch',
        key="metals_editor"
    )
    
    st.markdown("#### Tax Settings")
    col1, col2 = st.columns(2)
    with col1:
        cgst = st.number_input("CGST %", value=st.session_state.cgst, min_value=0.0, format="%.2f")
    with col2:
        sgst = st.number_input("SGST %", value=st.session_state.sgst, min_value=0.0, format="%.2f")
    
    if st.button("💾 Save Settings", width='stretch'):
        # Update metal settings
        new_settings = {}
        for _, row in edited_metals.iterrows():
            if row['Metal']:
                new_settings[row['Metal']] = {
                    'rate': float(row['Rate (per gram)']),
                    'wastage': float(row['Wastage %']),
                    'making': float(row['Making %'])
                }
        st.session_state.metal_settings = new_settings
        st.session_state.cgst = cgst
        st.session_state.sgst = sgst
        st.success("✅ Settings saved successfully!")
    
    # Reset All Data Section
    st.markdown("---")
    st.markdown("#### 🔄 Reset User Database")
    st.warning("⚠️ **Danger Zone**: This will delete ALL your data including customers and invoices!")
    
    col1, col2 = st.columns([1, 3])
    with col1:
        if 'confirm_reset' not in st.session_state:
            st.session_state.confirm_reset = False
        
        if st.button("🗑️ Reset My Data", type="secondary"):
            st.session_state.confirm_reset = True
    
    with col2:
        if st.session_state.confirm_reset:
            st.error("⚠️ Are you absolutely sure? This action CANNOT be undone!")
            col_a, col_b, col_c = st.columns(3)
            with col_a:
                if st.button("✅ YES, DELETE EVERYTHING", type="primary"):
                    try:
                        # Delete the database file
                        db_path = st.session_state.db_path
                        if os.path.basename(db_path) == db_path and os.path.exists(db_path):
                            os.remove(db_path)
                        
                        # Reset session state
                        st.session_state.metal_settings = {
                            'Gold 24K': {'rate': 6500.0, 'wastage': 5.0, 'making': 10.0},
                            'Gold 22K': {'rate': 6000.0, 'wastage': 6.0, 'making': 12.0},
                            'Gold 18K': {'rate': 5500.0, 'wastage': 7.0, 'making': 14.0},
                            'Silver': {'rate': 75.0, 'wastage': 3.0, 'making': 8.0}
                        }
                        st.session_state.cgst = 1.5
                        st.session_state.sgst = 1.5
                        st.session_state.current_invoice_items = []
                        st.session_state.selected_customer_id = None
                        st.session_state.discount = 0.0
                        st.session_state.confirm_reset = False
                        
                        st.success("✅ All data has been reset! The page will reload...")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error resetting data: {str(e)}")
            
            with col_b:
                if st.button("❌ Cancel"):
                    st.session_state.confirm_reset = False
                    st.rerun()


# ============================================================================
# TAB 2: CUSTOMERS
# ============================================================================
with tab2:
    st.markdown("### 👥 Customer Management")
    
    # Action selector
    action = st.radio("Action", ["Add Customer", "Edit Customer", "Delete Customer"], horizontal=True)
    
    customers_df = db.get_customers()
    
    if action == "Add Customer":
        st.markdown("#### Add New Customer")
        
        col1, col2 = st.columns(2)
        with col1:
            existing_accounts = customers_df['account_no'].tolist() if not customers_df.empty else []
            new_account = generate_account_number(existing_accounts)
            account_no = st.text_input("Account Number", value=new_account)
            name = st.text_input("Customer Name *")
        
        with col2:
            phone = st.text_input("Phone Number * (10 digits)", max_chars=10, key="add_customer_phone")
            # Visual feedback for phone number
            if phone:
                phone_len = len(phone)
                if phone_len < 10:
                    st.warning(f"⚠️ {phone_len}/10 digits - Need {10 - phone_len} more")
                elif phone_len == 10:
                    if phone.isdigit():
                        st.success("✅ 10/10 digits - Valid!")
                    else:
                        st.error("❌ Only digits allowed")
            address = st.text_area("Address")
        
        if st.button("➕ Add Customer", width='stretch'):
            if not name or not phone:
                st.error("Name and phone are required")
            elif not validate_phone(phone):
                st.error("Phone must be exactly 10 digits")
            else:
                try:
                    db.add_customer(account_no, name, phone, address)
                    st.success(f"✅ Customer added successfully! Account: {account_no}")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error: {str(e)}")
    
    elif action == "Edit Customer":
        if customers_df.empty:
            st.info("No customers found. Add a customer first.")
        else:
            st.markdown("#### Edit Customer")
            
            # Type-ahead search
            search_query = st.text_input("🔍 Search Customer (type name or phone)", "", 
                                         help="Start typing to filter customers")
            
            # Filter customers based on search query
            if search_query:
                mask = (customers_df['name'].str.contains(search_query, case=False, na=False) | 
                       customers_df['phone'].str.contains(search_query, case=False, na=False))
                filtered_customers = customers_df[mask]
            else:
                filtered_customers = customers_df
            
            if not filtered_customers.empty:
                # Create options from filtered customers
                customer_options = {f"{row['name']} ({row['phone']})": row['id'] 
                                  for _, row in filtered_customers.iterrows()}
                
                selected = st.selectbox("Select Customer", options=list(customer_options.keys()), 
                                       key="edit_customer_select")
                
                if selected:
                    customer_id = customer_options[selected]
                    customer = db.get_customer_by_id(customer_id)
                    
                    col1, col2 = st.columns(2)
                    with col1:
                        account_no = st.text_input("Account Number", value=customer['account_no'])
                        name = st.text_input("Customer Name", value=customer['name'])
                    
                    with col2:
                        phone = st.text_input("Phone Number", value=customer['phone'], max_chars=10, key=f"edit_customer_phone_{customer_id}")
                        # Visual feedback for phone number
                        if phone:
                            phone_len = len(phone)
                            if phone_len < 10:
                                st.warning(f"⚠️ {phone_len}/10 digits - Need {10 - phone_len} more")
                            elif phone_len == 10:
                                if phone.isdigit():
                                    st.success("✅ 10/10 digits - Valid!")
                                else:
                                    st.error("❌ Only digits allowed")
                        address = st.text_area("Address", value=customer.get('address', ''))
                    
                    if st.button("💾 Update Customer", width='stretch'):
                        if not name or not phone:
                            st.error("Name and phone are required")
                        elif not validate_phone(phone):
                            st.error("Phone must be exactly 10 digits")
                        else:
                            try:
                                db.update_customer(customer_id, account_no, name, phone, address)
                                st.success("✅ Customer updated successfully!")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error: {str(e)}")
            else:
                st.info("No customers match your search")
    
    else:  # Delete Customer
        if customers_df.empty:
            st.info("No customers found.")
        else:
            st.markdown("#### Delete Customer")
            st.warning("⚠️ This will delete the customer and all their invoices!")
            
            # Type-ahead search
            search_query = st.text_input("🔍 Search Customer (type name or phone)", "", 
                                         key="delete_search",
                                         help="Start typing to filter customers")
            
            # Filter customers based on search query
            if search_query:
                mask = (customers_df['name'].str.contains(search_query, case=False, na=False) | 
                       customers_df['phone'].str.contains(search_query, case=False, na=False))
                filtered_customers = customers_df[mask]
            else:
                filtered_customers = customers_df
            
            if not filtered_customers.empty:
                # Create options from filtered customers
                customer_options = {f"{row['name']} ({row['phone']})": row['id'] 
                                  for _, row in filtered_customers.iterrows()}
                
                selected = st.selectbox("Select Customer to Delete", options=list(customer_options.keys()),
                                       key="delete_customer_select")
                
                if selected:
                    customer_id = customer_options[selected]
                    confirm = st.checkbox("I confirm I want to delete this customer")
                    
                    if confirm and st.button("🗑️ Delete Customer", width='stretch'):
                        db.delete_customer(customer_id)
                        st.success("✅ Customer deleted successfully!")
                        st.rerun()
            else:
                st.info("No customers match your search")
    
    # Show all customers
    st.markdown("---")
    st.markdown("#### All Customers")
    if not customers_df.empty:
        search = st.text_input("🔍 Search customers", "")
        if search:
            mask = (customers_df['name'].str.contains(search, case=False) | 
                   customers_df['phone'].str.contains(search, case=False))
            customers_df = customers_df[mask]
        
        st.dataframe(customers_df, width='stretch', hide_index=True)
    else:
        st.info("No customers yet. Add your first customer above!")


# ============================================================================
# TAB 3: CREATE INVOICE
# ============================================================================
with tab3:
    st.markdown("### 📝 Create Invoice")
    
    customers_df = db.get_customers()
    
    if customers_df.empty:
        st.warning("⚠️ No customers found. Please add a customer first in the Customers tab.")
    else:
        # Customer selection with type-ahead search
        st.markdown("#### Select Customer")
        
        # Type-ahead search
        search_query = st.text_input("🔍 Search Customer (type name or phone)", "", 
                                     key="create_invoice_search",
                                     help="Start typing to filter customers")
        
        # Filter customers based on search query
        if search_query:
            mask = (customers_df['name'].str.contains(search_query, case=False, na=False) | 
                   customers_df['phone'].str.contains(search_query, case=False, na=False))
            filtered_customers = customers_df[mask]
        else:
            filtered_customers = customers_df
        
        if not filtered_customers.empty:
            customer_options = {f"{row['name']} ({row['phone']})": row['id'] 
                              for _, row in filtered_customers.iterrows()}
            
            selected_customer = st.selectbox(
                "Select Customer *",
                options=[""] + list(customer_options.keys()),
                key="create_invoice_customer_select"
            )
        else:
            selected_customer = ""
            st.info("No customers match your search")
        
        if selected_customer:
            st.session_state.selected_customer_id = customer_options[selected_customer]
            
            # New invoice button
            col1, col2, col3 = st.columns([1, 1, 6])
            with col1:
                if st.button("🆕 New Invoice"):
                    st.session_state.current_invoice_items = []
                    st.session_state.discount = 0.0
                    st.rerun()
            
            st.markdown("#### Add Items")
            
            # Item entry form
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                metal = st.selectbox("Metal *", options=list(st.session_state.metal_settings.keys()))
            
            with col2:
                weight = st.number_input("Weight (grams) *", min_value=0.0, format="%.3f")
            
            settings = st.session_state.metal_settings[metal]
            
            with col3:
                rate = st.number_input("Rate/gram", value=settings['rate'], format="%.2f")
            
            with col4:
                wastage = st.number_input("Wastage %", value=settings['wastage'], format="%.2f")
            
            col5, col6, col7 = st.columns([1, 1, 2])
            
            with col5:
                making = st.number_input("Making %", value=settings['making'], format="%.2f")
            
            # Calculate totals
            if weight > 0 and rate > 0:
                totals = calculate_item_totals(weight, rate, wastage, making)
                
                with col6:
                    st.metric("Item Value", format_currency(totals['item_value']))
                
                with col7:
                    st.metric("Line Total", format_currency(totals['line_total']))
                
                if st.button("➕ Add Item to Invoice", width='stretch'):
                    item = {
                        'metal': metal,
                        'weight': weight,
                        'rate': rate,
                        'wastage_percent': wastage,
                        'making_percent': making,
                        'item_value': totals['item_value'],
                        'wastage_amount': totals['wastage_amount'],
                        'making_amount': totals['making_amount'],
                        'line_total': totals['line_total']
                    }
                    st.session_state.current_invoice_items.append(item)
                    st.success("✅ Item added!")
                    st.rerun()
            
            # Show current items
            if st.session_state.current_invoice_items:
                st.markdown("#### Current Invoice Items")
                
                items_display = []
                for i, item in enumerate(st.session_state.current_invoice_items):
                    items_display.append({
                        'No.': i + 1,
                        'Metal': item['metal'],
                        'Weight': f"{item['weight']:.3f}g",
                        'Rate': format_currency(item['rate']),
                        'Wastage': format_currency(item['wastage_amount']),
                        'Making': format_currency(item['making_amount']),
                        'Total': format_currency(item['line_total'])
                    })
                
                st.dataframe(pd.DataFrame(items_display), width='stretch', hide_index=True)
                
                # Remove item button
                if st.button("🗑️ Remove Last Item"):
                    st.session_state.current_invoice_items.pop()
                    st.rerun()
                
                # Invoice summary
                st.markdown("#### Invoice Summary")
                
                subtotal = sum(item['line_total'] for item in st.session_state.current_invoice_items)
                
                col1, col2 = st.columns(2)
                with col1:
                    discount_pct = st.number_input("Discount %", min_value=0.0, value=st.session_state.discount, format="%.2f")
                    st.session_state.discount = discount_pct
                
                discount_amt = subtotal * (discount_pct / 100)
                taxable_amount = subtotal - discount_amt
                cgst_amt = taxable_amount * (st.session_state.cgst / 100)
                sgst_amt = taxable_amount * (st.session_state.sgst / 100)
                total = taxable_amount + cgst_amt + sgst_amt
                
                # Display summary
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col2:
                    st.markdown(f"**Subtotal:** {format_currency(subtotal)}")
                    if discount_pct > 0:
                        st.markdown(f"**Discount ({discount_pct}%):** -{format_currency(discount_amt)}")
                        st.markdown(f"**Taxable Amount:** {format_currency(taxable_amount)}")
                    st.markdown(f"**CGST ({st.session_state.cgst}%):** {format_currency(cgst_amt)}")
                    st.markdown(f"**SGST ({st.session_state.sgst}%):** {format_currency(sgst_amt)}")
                    st.markdown(f"### **Total:** {format_currency(total)}")
                
                # Save invoice
                if st.button("💾 Save Invoice", width='stretch'):
                    try:
                        invoice_no = generate_invoice_number()
                        db.save_invoice(
                            st.session_state.selected_customer_id,
                            invoice_no,
                            st.session_state.current_invoice_items,
                            st.session_state.cgst,
                            st.session_state.sgst,
                            discount_pct
                        )
                        st.success(f"✅ Invoice saved! Invoice No: **{invoice_no}**")
                        st.session_state.current_invoice_items = []
                        st.session_state.discount = 0.0
                        st.balloons()
                    except Exception as e:
                        st.error(f"Error saving invoice: {str(e)}")


# ============================================================================
# TAB 4: VIEW INVOICES
# ============================================================================
with tab4:
    st.markdown("### 📋 View Invoices")
    
    invoices_df = db.get_invoices()
    
    if invoices_df.empty:
        st.info("No invoices yet. Create your first invoice in the Create Invoice tab!")
    else:
        # Search
        search = st.text_input("🔍 Search invoices", "")
        if search:
            mask = (invoices_df['invoice_no'].str.contains(search, case=False) | 
                   invoices_df['customer_name'].str.contains(search, case=False, na=False) |
                   invoices_df['customer_phone'].str.contains(search, case=False, na=False))
            invoices_df = invoices_df[mask]
        
        # Display invoices
        for _, row in invoices_df.iterrows():
            with st.expander(
                f"📄 {row['invoice_no']} | {row['customer_name']} | {format_currency(row['total'])} | {row['date']}"
            ):
                invoice, items_df, customer = db.get_invoice_by_number(row['invoice_no'])
                
                # Customer info
                col1, col2 = st.columns(2)
                with col1:
                    st.markdown(f"**Customer:** {customer['name']}")
                    st.markdown(f"**Phone:** {customer['phone']}")
                with col2:
                    st.markdown(f"**Account:** {customer['account_no']}")
                    st.markdown(f"**Date:** {invoice['date']}")
                
                st.markdown("---")
                
                # Items table
                st.markdown("**Items:**")
                items_display = []
                for _, item in items_df.iterrows():
                    items_display.append({
                        'No.': int(item['item_no']),
                        'Metal': item['metal'],
                        'Weight': f"{item['weight']:.3f}g",
                        'Rate': format_currency(item['rate']),
                        'Item Value': format_currency(item['item_value']),
                        'Wastage': format_currency(item['wastage_amount']),
                        'Making': format_currency(item['making_amount']),
                        'Total': format_currency(item['line_total'])
                    })
                
                st.dataframe(pd.DataFrame(items_display), width='stretch', hide_index=True)
                
                # Summary
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col2:
                    st.markdown(f"**Subtotal:** {format_currency(invoice['subtotal'])}")
                    if invoice['discount_percent'] > 0:
                        st.markdown(f"**Discount ({invoice['discount_percent']}%):** -{format_currency(invoice['discount_amount'])}")
                    st.markdown(f"**CGST ({invoice['cgst_percent']}%):** {format_currency(invoice['cgst_amount'])}")
                    st.markdown(f"**SGST ({invoice['sgst_percent']}%):** {format_currency(invoice['sgst_amount'])}")
                    st.markdown(f"### **Total:** {format_currency(invoice['total'])}")
                
                st.markdown("---")
                
                # Action buttons
                col1, col2, col3, col4 = st.columns(4)
                
                # PDF download (direct download)
                with col1:
                    pdf_buffer = create_invoice_pdf(invoice, items_df, customer)
                    st.download_button(
                        label="📄 Download PDF",
                        data=pdf_buffer,
                        file_name=f"{row['invoice_no']}.pdf",
                        mime="application/pdf",
                        key=f"dl_{row['invoice_no']}"
                    )
                
                # Print (opens in new tab with printer selection)
                with col2:
                    pdf_buffer_print = create_invoice_pdf(invoice, items_df, customer)
                    import base64
                    b64 = base64.b64encode(pdf_buffer_print.read()).decode()
                    # JavaScript to trigger print dialog which allows printer selection
                    print_js = f"""
                    <script>
                    function printPDF_{row['invoice_no'].replace('-', '_')}() {{
                        var pdfWindow = window.open("");
                        pdfWindow.document.write(
                            "<iframe width='100%' height='100%' src='data:application/pdf;base64,{b64}'></iframe>"
                        );
                        setTimeout(function() {{
                            pdfWindow.print();
                        }}, 250);
                    }}
                    </script>
                    <button onclick="printPDF_{row['invoice_no'].replace('-', '_')}()" 
                            style="background-color:#ff4b4b; color:white; border:none; 
                            padding:0.5rem 1rem; border-radius:0.5rem; cursor:pointer;">
                        🖨️ Print
                    </button>
                    """
                    st.markdown(print_js, unsafe_allow_html=True)
                
                # Thermal print
                with col3:
                    from pdf_generator import create_thermal_invoice_pdf
                    thermal_buffer = create_thermal_invoice_pdf(invoice, items_df, customer)
                    st.download_button(
                        label="🧾 Thermal Print",
                        data=thermal_buffer,
                        file_name=f"{row['invoice_no']}_thermal.pdf",
                        mime="application/pdf",
                        key=f"thermal_{row['invoice_no']}"
                    )
                
                # Edit invoice button
                with col4:
                    if st.button("✏️ Edit Invoice", key=f"edit_{row['invoice_no']}", use_container_width=True):
                        st.session_state.editing_invoice_id = invoice['id']
                        st.session_state.editing_invoice_no = row['invoice_no']
                        st.rerun()
                
                    # Edit invoice form
                    if st.session_state.get('editing_invoice_id') == invoice['id']:
                        st.markdown("---")
                        st.markdown("### ✏️ Edit Invoice")
                        
                        # Load items into editable list - use session state to persist changes
                        if 'temp_edit_items' not in st.session_state or st.session_state.get('temp_edit_items_invoice_id') != invoice['id']:
                            edit_items = []
                            for _, item in items_df.iterrows():
                                edit_items.append({
                                    'metal': item['metal'],
                                    'weight': float(item['weight']),
                                    'rate': float(item['rate']),
                                    'wastage_percent': float(item['wastage_percent']),
                                    'making_percent': float(item['making_percent']),
                                    'item_value': float(item['item_value']),
                                    'wastage_amount': float(item['wastage_amount']),
                                    'making_amount': float(item['making_amount']),
                                    'line_total': float(item['line_total'])
                                })
                            st.session_state.temp_edit_items = edit_items
                            st.session_state.temp_edit_items_invoice_id = invoice['id']
                        else:
                            edit_items = st.session_state.temp_edit_items
                        
                        # Convert to DataFrame for inline editing
                        df_edit = pd.DataFrame(edit_items)
                        if df_edit.empty:
                            df_edit = pd.DataFrame(columns=[
                                'metal', 'weight', 'rate', 'wastage_percent', 'making_percent',
                                'item_value', 'wastage_amount', 'making_amount', 'line_total'
                            ])
                        
                        # Ensure columns exist and in desired order
                        cols_order = ['metal', 'weight', 'rate', 'wastage_percent', 'making_percent',
                                      'item_value', 'wastage_amount', 'making_amount', 'line_total']
                        for c in cols_order:
                            if c not in df_edit.columns:
                                df_edit[c] = 0.0 if c not in ('metal',) else ''
                        df_edit = df_edit[cols_order]
                        
                        st.markdown("**Edit Items Inline:**")
                        
                        # Use data_editor to let user edit rows inline.
                        # Editable columns: metal, weight, rate, wastage_percent, making_percent.
                        # Computed columns are displayed as read-only and will be recalculated live.
                        try:
                            edited_df = st.data_editor(
                                df_edit,
                                column_config={
                                    'metal': st.column_config.TextColumn('metal'),
                                    'weight': st.column_config.NumberColumn('weight', format="%.3f"),
                                    'rate': st.column_config.NumberColumn('rate', format="%.2f"),
                                    'wastage_percent': st.column_config.NumberColumn('wastage_percent', format="%.2f"),
                                    'making_percent': st.column_config.NumberColumn('making_percent', format="%.2f"),
                                    'item_value': st.column_config.NumberColumn('item_value', format="%.2f", disabled=True),
                                    'wastage_amount': st.column_config.NumberColumn('wastage_amount', format="%.2f", disabled=True),
                                    'making_amount': st.column_config.NumberColumn('making_amount', format="%.2f", disabled=True),
                                    'line_total': st.column_config.NumberColumn('line_total', format="%.2f", disabled=True),
                                },
                                hide_index=True,
                                use_container_width=True,
                                key=f"items_editor_{invoice['id']}"
                            )
                        except Exception:
                            # Fallback if column_config API isn't available in older Streamlit versions
                            edited_df = st.data_editor(
                                df_edit,
                                hide_index=True,
                                use_container_width=True,
                                key=f"items_editor_{invoice['id']}"
                            )
                        
                        # Recalculate totals for rows based on edited numeric inputs
                        recalculated_rows = []
                        for _, row in edited_df.iterrows():
                            try:
                                metal = str(row.get('metal', '')).strip() or list(st.session_state.metal_settings.keys())[0]
                                # Some values may be NaN or empty strings; coerce safely to floats
                                try:
                                    weight = float(row.get('weight') or 0.0)
                                except Exception:
                                    weight = 0.0
                                try:
                                    rate = float(row.get('rate') or 0.0)
                                except Exception:
                                    rate = 0.0
                                try:
                                    wastage_pct = float(row.get('wastage_percent') or 0.0)
                                except Exception:
                                    wastage_pct = 0.0
                                try:
                                    making_pct = float(row.get('making_percent') or 0.0)
                                except Exception:
                                    making_pct = 0.0
                                
                                if weight > 0 and rate > 0:
                                    totals = calculate_item_totals(weight, rate, wastage_pct, making_pct)
                                    item_value = totals['item_value']
                                    wastage_amount = totals['wastage_amount']
                                    making_amount = totals['making_amount']
                                    line_total = totals['line_total']
                                else:
                                    item_value = 0.0
                                    wastage_amount = 0.0
                                    making_amount = 0.0
                                    line_total = 0.0
                            except Exception:
                                item_value = 0.0
                                wastage_amount = 0.0
                                making_amount = 0.0
                                line_total = 0.0
                            
                            recalculated_rows.append({
                                'metal': metal,
                                'weight': weight,
                                'rate': rate,
                                'wastage_percent': wastage_pct,
                                'making_percent': making_pct,
                                'item_value': item_value,
                                'wastage_amount': wastage_amount,
                                'making_amount': making_amount,
                                'line_total': line_total
                            })
                        
                        # Persist recalculated rows back to session state
                        st.session_state.temp_edit_items = recalculated_rows
                        
                        # Display recalculated table (read-friendly)
                        items_edit_display = []
                        for i, item in enumerate(recalculated_rows):
                            items_edit_display.append({
                                'No.': i + 1,
                                'Metal': item['metal'],
                                'Weight': f"{item['weight']:.3f}g",
                                'Rate': format_currency(item['rate']),
                                'Item Value': format_currency(item['item_value']),
                                'Wastage': format_currency(item['wastage_amount']),
                                'Making': format_currency(item['making_amount']),
                                'Total': format_currency(item['line_total'])
                            })
                        st.dataframe(pd.DataFrame(items_edit_display), width='stretch', hide_index=True)
                        
                        # Add / remove item buttons (affect session_state.temp_edit_items)
                        col_a, col_b = st.columns([1, 1])
                        with col_a:
                            if st.button("➕ Add Empty Item", key=f"add_empty_{invoice['id']}"):
                                st.session_state.temp_edit_items.append({
                                    'metal': list(st.session_state.metal_settings.keys())[0],
                                    'weight': 0.0,
                                    'rate': 0.0,
                                    'wastage_percent': 0.0,
                                    'making_percent': 0.0,
                                    'item_value': 0.0,
                                    'wastage_amount': 0.0,
                                    'making_amount': 0.0,
                                    'line_total': 0.0
                                })
                                st.rerun()
                        with col_b:
                            if st.button("🗑️ Remove Last Item", key=f"remove_last_{invoice['id']}"):
                                if st.session_state.temp_edit_items:
                                    st.session_state.temp_edit_items.pop()
                                st.rerun()
                        
                        # Edit discount (live)
                        edit_discount = st.number_input(
                            "Discount %", 
                            min_value=0.0, 
                            value=float(invoice.get('discount_percent', 0.0)), 
                            format="%.2f",
                            key=f"edit_discount_{invoice['id']}"
                        )
                        
                        # Calculate invoice summary from recalculated rows
                        subtotal_edit = sum(item['line_total'] for item in st.session_state.temp_edit_items) if st.session_state.temp_edit_items else 0.0
                        discount_amt_edit = subtotal_edit * (edit_discount / 100)
                        taxable_edit = subtotal_edit - discount_amt_edit
                        cgst_amt_edit = taxable_edit * (invoice.get('cgst_percent', 0.0) / 100)
                        sgst_amt_edit = taxable_edit * (invoice.get('sgst_percent', 0.0) / 100)
                        total_edit = taxable_edit + cgst_amt_edit + sgst_amt_edit
                        
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col2:
                            st.markdown(f"**Subtotal:** {format_currency(subtotal_edit)}")
                            if edit_discount > 0:
                                st.markdown(f"**Discount ({edit_discount}%):** -{format_currency(discount_amt_edit)}")
                                st.markdown(f"**Taxable Amount:** {format_currency(taxable_edit)}")
                            st.markdown(f"**CGST ({invoice.get('cgst_percent', 0.0)}%):** {format_currency(cgst_amt_edit)}")
                            st.markdown(f"**SGST ({invoice.get('sgst_percent', 0.0)}%):** {format_currency(sgst_amt_edit)}")
                            st.markdown(f"### **Total:** {format_currency(total_edit)}")
                        
                        # Save changes
                        col1, col2 = st.columns(2)
                        with col1:
                            if st.button("💾 Save Changes", key=f"save_edit_{invoice['id']}"):
                                try:
                                    # Validate: must have at least one non-zero item
                                    valid_items = [it for it in st.session_state.temp_edit_items if it['line_total'] > 0]
                                    if not valid_items:
                                        st.error("Invoice must have at least one non-zero item")
                                    else:
                                        db.update_invoice(
                                            invoice['id'],
                                            st.session_state.temp_edit_items,
                                            invoice.get('cgst_percent', 0.0),
                                            invoice.get('sgst_percent', 0.0),
                                            edit_discount
                                        )
                                        st.success("✅ Invoice updated successfully!")
                                        # Clean up edit state
                                        for k in ('editing_invoice_id', 'editing_invoice_no', 'temp_edit_items', 'temp_edit_items_invoice_id'):
                                            if k in st.session_state:
                                                del st.session_state[k]
                                        st.rerun()
                                except Exception as e:
                                    st.error(f"Error updating invoice: {str(e)}")
                        
                        with col2:
                            if st.button("❌ Cancel Edit", key=f"cancel_edit_{invoice['id']}"):
                                # discard changes
                                for k in ('editing_invoice_id', 'editing_invoice_no', 'temp_edit_items', 'temp_edit_items_invoice_id'):
                                    if k in st.session_state:
                                        del st.session_state[k]
                                st.rerun()


# ============================================================================
# TAB 5: DATABASE MANAGEMENT
# ============================================================================
with tab5:
    st.markdown("### 🗄️ Database Management")
    
    from datetime import datetime
    
    # Show current database info
    st.info(f"💾 Current Database: `{st.session_state.db_path}`")
    
    # Backup & Restore
    st.markdown("#### Backup & Restore")
    col1, col2 = st.columns(2)
    
    with col1:
        st.markdown("**Create Backup**")
        if st.button("💾 Backup Database", width='stretch'):
            import shutil
            from datetime import datetime
            backup_name = f"backup_{st.session_state.username}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.db"
            try:
                db.export_database(backup_name)
                st.success(f"✅ Backup created: {backup_name}")
                
                # Provide download link
                with open(backup_name, 'rb') as f:
                    st.download_button(
                        label="⬇️ Download Backup",
                        data=f,
                        file_name=backup_name,
                        mime="application/octet-stream"
                    )
            except Exception as e:
                st.error(f"Error creating backup: {str(e)}")
    
    with col2:
        st.markdown("**Restore from Backup**")
        restore_file = st.file_uploader("📂 Upload Database Backup", type=['db'], key="db_restore")
        if restore_file is not None:
            if st.button("⬆️ Restore Database", width='stretch'):
                import tempfile
                try:
                    with tempfile.NamedTemporaryFile(delete=False, suffix='.db') as tmp_file:
                        tmp_file.write(restore_file.read())
                        tmp_path = tmp_file.name
                    
                    db.import_database(tmp_path)
                    os.unlink(tmp_path)  # Clean up temp file
                    st.success("✅ Database restored successfully!")
                    st.rerun()
                except Exception as e:
                    st.error(f"Error restoring database: {str(e)}")
    
    st.markdown("---")
    
    # Import/Export Data
    st.markdown("#### Import/Export Data")
    
    # Customers Import/Export
    st.markdown("**Customers**")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Customers (CSV)", width='stretch'):
            csv_data = db.export_customers_csv()
            st.download_button(
                label="💾 Download CSV",
                data=csv_data,
                file_name=f"customers_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.csv",
                mime="text/csv",
                key="download_customers_csv"
            )
    
    with col2:
        uploaded_customers = st.file_uploader("📤 Import Customers (CSV)", type=['csv'], key="import_customers")
        if uploaded_customers is not None:
            csv_content = uploaded_customers.read().decode('utf-8')
            if st.button("⬆️ Import Customers", width='stretch'):
                imported, errors = db.import_customers_csv(csv_content)
                if imported > 0:
                    st.success(f"✅ Imported {imported} customers")
                if errors:
                    st.warning(f"⚠️ {len(errors)} errors occurred")
                    for error in errors[:5]:
                        st.error(error)
                st.rerun()
    
    st.markdown("---")
    
    # Invoices Import/Export
    st.markdown("**Invoices**")
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("📥 Export Invoices (JSON)", width='stretch'):
            json_data = db.export_invoices_json()
            from datetime import datetime
            st.download_button(
                label="💾 Download JSON",
                data=json_data,
                file_name=f"invoices_{st.session_state.username}_{datetime.now().strftime('%Y%m%d')}.json",
                mime="application/json",
                key="download_invoices_json"
            )
    
    with col2:
        uploaded_invoices = st.file_uploader("📤 Import Invoices (JSON)", type=['json'], key="import_invoices")
        if uploaded_invoices is not None:
            json_content = uploaded_invoices.read().decode('utf-8')
            if st.button("⬆️ Import Invoices", width='stretch'):
                imported, errors = db.import_invoices_json(json_content)
                if imported > 0:
                    st.success(f"✅ Imported {imported} invoices")
                if errors:
                    st.warning(f"⚠️ {len(errors)} errors occurred")
                    for error in errors[:5]:
                        st.error(error)
                st.rerun()


# ============================================================================
# TAB 6: ADMIN PANEL (Only visible to admin)
# ============================================================================
if require_admin():
    with tab6:
        st.markdown("### 🔐 Admin Panel")
        
        # Create sub-tabs for different admin functions
        admin_tab1, admin_tab2, admin_tab3, admin_tab4 = st.tabs([
            "👥 User Management", 
            "➕ Create User",
            "🔑 Password Requests",
            "📊 Database Overview"
        ])
        
        with admin_tab1:
            st.markdown("#### User Management")
            
            # Pending Approvals
            pending_users = auth_db.get_pending_users()
            if not pending_users.empty:
                st.markdown("**Pending Approval Requests**")
                st.warning(f"⏳ {len(pending_users)} user(s) waiting for approval")
                
                for _, user in pending_users.iterrows():
                    with st.expander(f"👤 {user['username']} - {user['full_name']}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Username:** {user['username']}")
                            st.markdown(f"**Full Name:** {user['full_name']}")
                            st.markdown(f"**Email:** {user.get('email', 'N/A')}")
                        with col2:
                            st.markdown(f"**Phone:** {user.get('phone', 'N/A')}")
                            st.markdown(f"**Requested:** {user['created_at']}")
                        
                        col_a, col_b = st.columns(2)
                        with col_a:
                            if st.button("✅ Approve", key=f"approve_{user['id']}", width='stretch'):
                                auth_db.approve_user(user['id'], st.session_state.user_id)
                                st.success(f"✅ User {user['username']} approved!")
                                st.rerun()
                        with col_b:
                            if st.button("❌ Reject", key=f"reject_{user['id']}", width='stretch'):
                                auth_db.reject_user(user['id'])
                                st.success(f"❌ User {user['username']} rejected!")
                                st.rerun()
            else:
                st.info("✅ No pending approval requests")
            
            st.markdown("---")
            
            # All Users
            st.markdown("#### All Users")
            all_users = auth_db.get_all_users()
            
            if not all_users.empty:
                # Filter controls
                col1, col2 = st.columns(2)
                with col1:
                    status_filter = st.selectbox("Filter by Status", ["All", "Approved", "Pending"])
                with col2:
                    role_filter = st.selectbox("Filter by Role", ["All", "Admin", "User"])
                
                # Apply filters
                filtered_users = all_users.copy()
                if status_filter != "All":
                    filtered_users = filtered_users[filtered_users['status'] == status_filter.lower()]
                if role_filter != "All":
                    filtered_users = filtered_users[filtered_users['role'] == role_filter.lower()]
                
                # Display users
                for _, user in filtered_users.iterrows():
                    with st.expander(f"👤 {user['username']} ({user['role'].title()}) - {user['status'].title()}"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Username:** {user['username']}")
                            st.markdown(f"**Full Name:** {user['full_name']}")
                            st.markdown(f"**Email:** {user.get('email', 'N/A')}")
                            st.markdown(f"**Phone:** {user.get('phone', 'N/A')}")
                        with col2:
                            st.markdown(f"**Role:** {user['role'].title()}")
                            st.markdown(f"**Status:** {user['status'].title()}")
                            st.markdown(f"**Created:** {user['created_at']}")
                            if user.get('approved_at'):
                                st.markdown(f"**Approved:** {user['approved_at']}")
                        
                        # Admin actions
                        if user['username'] != 'admin':  # Prevent admin from modifying the default admin
                            st.markdown("**Actions:**")
                            col_a, col_b, col_c, col_d = st.columns(4)
                            
                            with col_a:
                                new_role = st.selectbox(
                                    "Change Role",
                                    ["user", "admin"],
                                    index=0 if user['role'] == 'user' else 1,
                                    key=f"role_{user['id']}"
                                )
                                if st.button("Update Role", key=f"update_role_{user['id']}"):
                                    auth_db.update_user_role(user['id'], new_role)
                                    st.success(f"✅ Role updated to {new_role}")
                                    st.rerun()
                            
                            with col_b:
                                # Reset password
                                if st.button("🔑 Reset Password", key=f"reset_pwd_{user['id']}"):
                                    st.session_state[f'show_reset_{user["id"]}'] = True
                                    st.rerun()
                                
                                if st.session_state.get(f'show_reset_{user["id"]}'):
                                    new_pwd = st.text_input("New Password", type="password", key=f"new_pwd_{user['id']}")
                                    if st.button("Set Password", key=f"set_pwd_{user['id']}"):
                                        if len(new_pwd) >= 6:
                                            from auth import hash_password
                                            new_hash = hash_password(new_pwd)
                                            auth_db.update_user_password(user['id'], new_hash)
                                            st.success("✅ Password updated!")
                                            del st.session_state[f'show_reset_{user["id"]}']
                                            st.rerun()
                                        else:
                                            st.error("Password must be at least 6 characters")
                            
                            with col_c:
                                # Login as user (without password)
                                if st.button("👤 Login as User", key=f"login_as_{user['id']}", help="Access this user's account"):
                                    # Store admin info to allow return
                                    st.session_state.admin_return_id = st.session_state.user_id
                                    st.session_state.admin_return_username = st.session_state.username
                                    st.session_state.admin_return_role = st.session_state.user_role
                                    st.session_state.admin_return_fullname = st.session_state.user_full_name
                                    st.session_state.admin_return_dbpath = st.session_state.db_path
                                    
                                    # Switch to user account
                                    st.session_state.user_id = user['id']
                                    st.session_state.username = user['username']
                                    st.session_state.user_role = user['role']
                                    st.session_state.user_full_name = user['full_name']
                                    st.session_state.db_path = f'jewelcalc_user_{user["id"]}.db'
                                    
                                    st.success(f"✅ Logged in as {user['username']}")
                                    st.info("💡 Use 'Return to Admin' button in sidebar to go back")
                                    st.rerun()
                            
                            with col_d:
                                # View user's database
                                user_db_path = f'jewelcalc_user_{user["id"]}.db'
                                if os.path.exists(user_db_path):
                                    st.info(f"📊 Database exists")
                                else:
                                    st.warning("No database yet")
                            
                            # Delete button in separate row
                            st.markdown("---")
                            if st.button("🗑️ Delete User", key=f"delete_{user['id']}", type="secondary"):
                                if st.session_state.get(f'confirm_delete_{user["id"]}'):
                                    auth_db.reject_user(user['id'])
                                    st.success(f"✅ User deleted")
                                    st.rerun()
                                else:
                                    st.session_state[f'confirm_delete_{user["id"]}'] = True
                                    st.warning("Click again to confirm")
            else:
                st.info("No users in the system")
        
        with admin_tab2:
            st.markdown("#### Create New User")
            st.info("💡 Create a new user account with immediate approval (bypasses signup workflow)")
            
            with st.form("admin_create_user_form"):
                col1, col2 = st.columns(2)
                with col1:
                    create_username = st.text_input("Username *")
                    create_full_name = st.text_input("Full Name *")
                    create_email = st.text_input("Email")
                with col2:
                    create_phone = st.text_input("Phone Number (10 digits)", max_chars=10)
                    create_role = st.selectbox("Role", ["user", "admin"])
                    create_password = st.text_input("Password *", type="password")
                
                create_user_submit = st.form_submit_button("➕ Create User", use_container_width=True)
                
                if create_user_submit:
                    if not create_username or not create_full_name or not create_password:
                        st.error("Username, full name, and password are required")
                    elif len(create_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    else:
                        try:
                            # Check if username already exists
                            existing_user = auth_db.get_user_by_username(create_username)
                            if existing_user:
                                st.error("❌ Username already exists. Please choose a different username.")
                            else:
                                # Create new user with immediate approval
                                from auth import hash_password
                                password_hash = hash_password(create_password)
                                user_id = auth_db.add_user_with_approval(
                                    create_username, 
                                    password_hash, 
                                    create_full_name, 
                                    create_email, 
                                    create_phone, 
                                    create_role,
                                    st.session_state.user_id
                                )
                                st.success(f"✅ User '{create_username}' created successfully! User ID: {user_id}")
                                st.warning("⚠️ **Important**: Securely communicate the password to the user through a secure channel (not shown here for security reasons). Consider requiring users to change their password on first login.")
                                st.balloons()
                        except Exception as e:
                            st.error(f"Error creating user: {str(e)}")
        
        with admin_tab3:
            st.markdown("#### Password Reset Requests")
            
            # Replace the existing line:
            # pending_resets = auth_db.get_pending_password_reset_requests()
            
            # With this guarded approach:
            try:
                pending_resets = auth_db.get_pending_password_reset_requests()
            except AttributeError as err:
                # Helpful debug information for the admin UI (remove after fixing)
                st.error("Internal error: authentication DB object is missing expected method get_pending_password_reset_requests().")
                st.write("auth_db type:", type(auth_db))
                st.write("auth_db dir:", sorted(dir(auth_db)))
                # Fall back to an empty dataframe so UI continues to load
                import pandas as pd
                pending_resets = pd.DataFrame()
            
            if not pending_resets.empty:
                st.warning(f"⏳ {len(pending_resets)} password reset request(s) pending")
                
                for _, request in pending_resets.iterrows():
                    with st.expander(f"🔑 {request['username']} - {request['request_type'].title()} Request"):
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown(f"**Username:** {request['username']}")
                            st.markdown(f"**Request Type:** {request['request_type'].title()}")
                            st.markdown(f"**Email:** {request.get('email', 'N/A')}")
                        with col2:
                            st.markdown(f"**Phone:** {request.get('phone', 'N/A')}")
                            st.markdown(f"**Requested:** {request['requested_at']}")
                        
                        st.markdown("---")
                        st.markdown("**Actions:**")
                        
                        if request['request_type'] in ['password', 'both']:
                            # Show password reset form
                            col_a, col_b, col_c = st.columns(3)
                            with col_a:
                                new_password = st.text_input(
                                    "Set New Password", 
                                    type="password", 
                                    key=f"reset_pwd_{request['id']}"
                                )
                            with col_b:
                                if st.button("✅ Reset Password", key=f"do_reset_{request['id']}"):
                                    if len(new_password) >= 6:
                                        from auth import hash_password
                                        new_hash = hash_password(new_password)
                                        auth_db.resolve_password_reset_request(
                                            request['id'], 
                                            st.session_state.user_id, 
                                            new_hash
                                        )
                                        st.success(f"✅ Password reset for {request['username']}")
                                        st.warning("⚠️ **Important**: Securely communicate the new password to the user through email, phone, or other secure channel.")
                                        st.rerun()
                                    else:
                                        st.error("Password must be at least 6 characters")
                            with col_c:
                                if st.button("❌ Reject Request", key=f"reject_reset_{request['id']}"):
                                    auth_db.reject_password_reset_request(request['id'])
                                    st.success("Request rejected")
                                    st.rerun()
                        else:
                            # Username request - just show the username
                            st.info(f"👤 Username for this user is: **{request['username']}**")
                            col_a, col_b = st.columns(2)
                            with col_a:
                                if st.button("✅ Mark as Resolved", key=f"resolve_{request['id']}"):
                                    auth_db.resolve_password_reset_request(
                                        request['id'], 
                                        st.session_state.user_id
                                    )
                                    st.success("Request resolved")
                                    st.rerun()
                            with col_b:
                                if st.button("❌ Reject Request", key=f"reject_reset_{request['id']}"):
                                    auth_db.reject_password_reset_request(request['id'])
                                    st.success("Request rejected")
                                    st.rerun()
            else:
                st.info("✅ No pending password reset requests")
        
        with admin_tab4:
            st.markdown("#### Database Overview")
            
            # Get all user databases
            import glob
            user_dbs = glob.glob('jewelcalc_user_*.db')
            
            if user_dbs:
                st.markdown(f"**Total User Databases:** {len(user_dbs)}")
                
                # Show statistics for each user database
                for db_file in user_dbs:
                    try:
                        user_db = Database(db_file)
                        customers = user_db.get_customers()
                        invoices = user_db.get_invoices()
                        
                        user_id = db_file.replace('jewelcalc_user_', '').replace('.db', '')
                        user_info = all_users[all_users['id'] == int(user_id)]
                        username = user_info.iloc[0]['username'] if not user_info.empty else f"User {user_id}"
                        
                        with st.expander(f"📊 {username} - {db_file}"):
                            col1, col2, col3 = st.columns(3)
                            with col1:
                                st.metric("Customers", len(customers))
                            with col2:
                                st.metric("Invoices", len(invoices))
                            with col3:
                                if not invoices.empty:
                                    total_revenue = invoices['total'].sum()
                                    st.metric("Total Revenue", format_currency(total_revenue))
                                else:
                                    st.metric("Total Revenue", format_currency(0))
                    except Exception as e:
                        st.error(f"Error reading {db_file}: {str(e)}")
            else:
                st.info("No user databases found")
