"""Authentication module for JewelCalc"""
import hashlib
import os
import streamlit as st


def hash_password(password):
    """Hash password using PBKDF2-SHA256 (secure for passwords)"""
    # Generate a random salt
    salt = os.urandom(32)
    # Use PBKDF2 with 100,000 iterations for strong password hashing
    pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
    # Store salt and hash together
    return salt.hex() + ':' + pwd_hash.hex()


def verify_password(password, password_hash):
    """Verify password against hash"""
    try:
        # Split salt and hash
        salt_hex, hash_hex = password_hash.split(':')
        salt = bytes.fromhex(salt_hex)
        stored_hash = bytes.fromhex(hash_hex)
        # Hash the provided password with the stored salt
        pwd_hash = hashlib.pbkdf2_hmac('sha256', password.encode('utf-8'), salt, 100000)
        # Compare hashes
        return pwd_hash == stored_hash
    except (ValueError, AttributeError):
        # Backward compatibility for legacy SHA256 hashes (insecure, deprecated)
        # This is only for supporting old password hashes during migration
        # TODO: Remove this after all users have migrated to PBKDF2
        if len(password_hash) == 64:
            # Legacy SHA256 verification (not recommended for new passwords)
            return hashlib.sha256(password.encode()).hexdigest() == password_hash
        return False


def show_login_page(db):
    """Display login page"""
    st.markdown('<div class="main-header"><h1>💎 JewelCalc - Login</h1></div>', unsafe_allow_html=True)
    
    # Create tabs for login, signup, and forgot password
    tab1, tab2, tab3 = st.tabs(["🔐 Login", "📝 Sign Up", "🔑 Forgot Password"])
    
    with tab1:
        st.markdown("### Login to Your Account")
        
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if not username or not password:
                    st.error("Please enter both username and password")
                else:
                    user = db.get_user_by_username(username)
                    
                    if user is None:
                        st.error("❌ Invalid username or password")
                    elif user['status'] == 'pending':
                        st.warning("⏳ Your account is pending approval by an administrator")
                    elif user['status'] != 'approved':
                        st.error("❌ Your account has been deactivated")
                    elif not verify_password(password, user['password_hash']):
                        st.error("❌ Invalid username or password")
                    else:
                        # Login successful
                        st.session_state.logged_in = True
                        st.session_state.user_id = user['id']
                        st.session_state.username = user['username']
                        st.session_state.user_role = user['role']
                        st.session_state.user_full_name = user['full_name']
                        
                        # Set user-specific database path
                        if user['role'] == 'admin':
                            st.session_state.db_path = 'jewelcalc_admin.db'
                        else:
                            st.session_state.db_path = f'jewelcalc_user_{user["id"]}.db'
                        
                        st.success(f"✅ Welcome back, {user['full_name']}!")
                        st.rerun()
    
    with tab2:
        st.markdown("### Create New Account")
        st.info("📝 After signing up, an administrator will need to approve your account before you can login.")
        
        with st.form("signup_form"):
            col1, col2 = st.columns(2)
            with col1:
                new_username = st.text_input("Username *", help="Choose a unique username")
                new_full_name = st.text_input("Full Name *")
            with col2:
                new_email = st.text_input("Email")
                new_phone = st.text_input("Phone Number (10 digits)", max_chars=10, help="Enter exactly 10 digits")
            
            new_password = st.text_input("Password *", type="password", help="Choose a strong password")
            confirm_password = st.text_input("Confirm Password *", type="password")
            
            signup_submit = st.form_submit_button("Sign Up", use_container_width=True)
            
            if signup_submit:
                if not new_username or not new_full_name or not new_password:
                    st.error("Please fill in all required fields (*)")
                elif new_password != confirm_password:
                    st.error("Passwords do not match")
                elif len(new_password) < 6:
                    st.error("Password must be at least 6 characters long")
                elif new_phone and not new_phone.isdigit():
                    st.error("❌ Phone number must contain only digits")
                elif new_phone and len(new_phone) != 10:
                    st.error(f"❌ Phone number must be exactly 10 digits (currently {len(new_phone)} digits)")
                else:
                    try:
                        # Check if username already exists
                        existing_user = db.get_user_by_username(new_username)
                        if existing_user:
                            st.error("❌ Username already exists. Please choose a different username.")
                        else:
                            # Create new user
                            password_hash = hash_password(new_password)
                            db.add_user(new_username, password_hash, new_full_name, new_email, new_phone)
                            st.success("✅ Account created successfully! Please wait for admin approval to login.")
                            st.info("💡 An administrator will review your request. You'll be notified once your account is approved.")
                    except Exception as e:
                        st.error(f"Error creating account: {str(e)}")
    
    with tab3:
        st.markdown("### Forgot Password/Username")
        st.info("📧 Submit a request to reset your password. An administrator will review and assist you.")
        
        with st.form("forgot_password_form"):
            forgot_username = st.text_input("Username (optional)", help="If you know your username")
            forgot_email = st.text_input("Email", help="Your registered email")
            forgot_phone = st.text_input("Phone (10 digits)", max_chars=10, help="Your registered phone number (10 digits)")
            
            request_type = st.radio(
                "What do you need help with?",
                ["Forgot Password", "Forgot Username", "Forgot Both"],
                horizontal=True
            )
            
            forgot_submit = st.form_submit_button("Submit Request", use_container_width=True)
            
            if forgot_submit:
                if not forgot_username and not forgot_email and not forgot_phone:
                    st.error("Please provide at least your username, email, or phone number")
                elif forgot_phone and (not forgot_phone.isdigit() or len(forgot_phone) != 10):
                    st.error("❌ Phone number must be exactly 10 digits")
                else:
                    try:
                        # Map request type to database format
                        request_type_map = {
                            "Forgot Password": "password",
                            "Forgot Username": "username",
                            "Forgot Both": "both"
                        }
                        
                        request_id = db.create_password_reset_request(
                            forgot_username, 
                            forgot_email, 
                            forgot_phone, 
                            request_type_map[request_type]
                        )
                        if request_id:
                            st.success("✅ Your request has been submitted! An administrator will review it shortly.")
                            st.info("💡 Please contact your administrator if you don't hear back within 24 hours.")
                        else:
                            st.error("❌ No user found with the provided information. Please check and try again.")
                    except Exception as e:
                        st.error(f"Error submitting request: {str(e)}")


def _clear_session_state():
    """Helper function to clear all session state variables"""
    for key in ['logged_in', 'user_id', 'username', 'user_role', 'user_full_name', 
               'admin_return_id', 'admin_return_username', 'admin_return_role', 
               'admin_return_fullname', 'admin_return_dbpath']:
        if key in st.session_state:
            del st.session_state[key]


def show_user_menu():
    """Display user menu in sidebar"""
    with st.sidebar:
        st.markdown("---")
        st.markdown(f"### 👤 {st.session_state.user_full_name}")
        st.info(f"**Role:** {st.session_state.user_role.title()}")
        
        # Show "Return to Admin" button if admin is logged in as another user
        if st.session_state.get('admin_return_id'):
            st.warning("⚠️ Viewing as user")
            if st.button("🔙 Return to Admin", use_container_width=True):
                # Restore admin session
                st.session_state.user_id = st.session_state.admin_return_id
                st.session_state.username = st.session_state.admin_return_username
                st.session_state.user_role = st.session_state.admin_return_role
                st.session_state.user_full_name = st.session_state.admin_return_fullname
                st.session_state.db_path = st.session_state.admin_return_dbpath
                
                # Clear return info
                for key in ['admin_return_id', 'admin_return_username', 'admin_return_role', 
                           'admin_return_fullname', 'admin_return_dbpath']:
                    if key in st.session_state:
                        del st.session_state[key]
                
                st.success("✅ Returned to admin account")
                st.rerun()
        
        # Profile/Settings expander
        with st.expander("⚙️ Profile Settings"):
            from database import Database
            auth_db = Database("jewelcalc_auth.db")
            user = auth_db.get_user_by_username(st.session_state.username)
            
            st.markdown("#### Update Profile")
            with st.form("update_profile_form"):
                profile_email = st.text_input("Email", value=user.get('email', ''))
                profile_phone = st.text_input("Phone Number (10 digits)", value=user.get('phone', ''), max_chars=10, help="Enter exactly 10 digits")
                
                update_profile_submit = st.form_submit_button("Update Profile")
                
                if update_profile_submit:
                    from utils import validate_phone
                    
                    if profile_phone and not validate_phone(profile_phone):
                        st.error("❌ Phone must be exactly 10 digits")
                    else:
                        # Update profile
                        auth_db.update_user_profile(
                            st.session_state.user_id,
                            email=profile_email if profile_email else None,
                            phone=profile_phone if profile_phone else None
                        )
                        st.success("✅ Profile updated successfully!")
                        st.rerun()
            
            st.markdown("---")
            st.markdown("#### Change Password")
            
            with st.form("change_password_form"):
                current_password = st.text_input("Current Password", type="password")
                new_password = st.text_input("New Password", type="password")
                confirm_new_password = st.text_input("Confirm New Password", type="password")
                
                change_pwd_submit = st.form_submit_button("Update Password")
                
                if change_pwd_submit:
                    if not current_password or not new_password or not confirm_new_password:
                        st.error("All fields are required")
                    elif new_password != confirm_new_password:
                        st.error("New passwords do not match")
                    elif len(new_password) < 6:
                        st.error("Password must be at least 6 characters long")
                    else:
                        # Verify current password
                        user = auth_db.get_user_by_username(st.session_state.username)
                        if not verify_password(current_password, user['password_hash']):
                            st.error("❌ Current password is incorrect")
                        else:
                            # Update password
                            new_hash = hash_password(new_password)
                            auth_db.update_user_password(st.session_state.user_id, new_hash)
                            st.success("✅ Password updated successfully!")
        
        # Show "Back to Admin Login" button only for admins (but not when viewing as another user)
        if st.session_state.get('user_role') == 'admin' and not st.session_state.get('admin_return_id'):
            if st.button("🔙 Back to Admin Login", use_container_width=True, type="secondary"):
                # Clear session state to return to login page
                _clear_session_state()
                st.rerun()
        
        if st.button("🚪 Logout", use_container_width=True):
            # Clear session state
            _clear_session_state()
            st.rerun()


def require_auth(db):
    """Decorator to require authentication"""
    if 'logged_in' not in st.session_state or not st.session_state.logged_in:
        show_login_page(db)
        return False
    return True


def require_admin():
    """Check if current user is admin"""
    return st.session_state.get('user_role') == 'admin'
