import os
import psycopg2
from dotenv import load_dotenv
from datetime import datetime
import getpass  # For secure password input

# Load environment variables
load_dotenv()

# Database connection function
def get_db_connection():
    return psycopg2.connect(
        host=os.getenv('DB_HOST'),
        database=os.getenv('DB_NAME'),
        user=os.getenv('DB_USER'),
        password=os.getenv('DB_PASSWORD'),
        port=os.getenv('DB_PORT')
    )

# User authentication
def login():
    print("\n=== Login ===")
    username = input("Username: ")
    password = getpass.getpass("Password: ")  # Hides password input
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute("SELECT user_id FROM users WHERE username = %s AND password = %s", (username, password))
        user = cur.fetchone()
        
        if user:
            print("\nLogin successful!")
            return user[0]  # Return user_id
        else:
            print("\nInvalid credentials. Would you like to register? (y/n)")
            choice = input().lower()
            if choice == 'y':
                return register()
            else:
                return None
    except Exception as e:
        print(f"\nError during login: {e}")
        return None
    finally:
        if conn:
            conn.close()

def register():
    print("\n=== Registration ===")
    username = input("Choose a username: ")
    password = getpass.getpass("Choose a password: ")
    full_name = input("Full name: ")
    
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Check if username exists
        cur.execute("SELECT username FROM users WHERE username = %s", (username,))
        if cur.fetchone():
            print("\nUsername already exists. Please choose another.")
            return None
        
        # Insert new user
        cur.execute(
            "INSERT INTO users (username, password, full_name) VALUES (%s, %s, %s) RETURNING user_id",
            (username, password, full_name)
        )
        user_id = cur.fetchone()[0]
        conn.commit()
        print("\nRegistration successful! You can now login.")
        return user_id
    except Exception as e:
        print(f"\nError during registration: {e}")
        return None
    finally:
        if conn:
            conn.close()

# Loan operations
def apply_for_loan(user_id):
    print("\n=== Apply for Loan ===")
    try:
        amount = float(input("Loan amount: $"))
        interest_rate = float(input("Interest rate (%): "))
        term_months = int(input("Loan term (months): "))
        
        conn = get_db_connection()
        cur = conn.cursor()
        cur.execute(
            """INSERT INTO loans (user_id, amount, interest_rate, term_months, start_date) 
            VALUES (%s, %s, %s, %s, %s) RETURNING loan_id""",
            (user_id, amount, interest_rate, term_months, datetime.now().date())
        )
        loan_id = cur.fetchone()[0]
        conn.commit()
        print(f"\nLoan application submitted! Loan ID: {loan_id}")
    except ValueError:
        print("\nInvalid input. Please enter numbers only.")
    except Exception as e:
        print(f"\nError applying for loan: {e}")
    finally:
        if conn:
            conn.close()

def make_payment(user_id):
    print("\n=== Make a Payment ===")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        # Get user's active loans
        cur.execute("""
            SELECT l.loan_id, l.amount, 
                   (l.amount - COALESCE(SUM(p.amount), 0)) as remaining_balance
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            WHERE l.user_id = %s AND l.status = 'active'
            GROUP BY l.loan_id, l.amount
            HAVING (l.amount - COALESCE(SUM(p.amount), 0)) > 0
        """, (user_id,))
        
        loans = cur.fetchall()
        
        if not loans:
            print("\nNo active loans with remaining balance.")
            return
        
        print("\nYour active loans with remaining balance:")
        print(f"{'ID':<8} {'Original Amt':<15} {'Remaining':<15}")
        print("-" * 40)
        for loan in loans:
            print(f"{loan[0]:<8} ${loan[1]:<14.2f} ${loan[2]:<14.2f}")
        
        loan_id = int(input("\nEnter loan ID to pay: "))
        amount = float(input("Payment amount: $"))
        
        # Verify loan belongs to user
        cur.execute("""
            SELECT l.loan_id 
            FROM loans l
            WHERE l.user_id = %s AND l.loan_id = %s
        """, (user_id, loan_id))
        
        if not cur.fetchone():
            print("\nInvalid loan ID or not your loan.")
            return
        
        # Record payment
        cur.execute(
            "INSERT INTO payments (loan_id, amount) VALUES (%s, %s)",
            (loan_id, amount)
        )
        conn.commit()
        print("\nPayment recorded successfully!")
    except ValueError:
        print("\nInvalid input. Please enter numbers only.")
    except Exception as e:
        print(f"\nError making payment: {e}")
    finally:
        if conn:
            conn.close()

def check_balance(user_id):
    print("\n=== Loan Balances ===")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT l.loan_id, l.amount, 
                   (l.amount - COALESCE(SUM(p.amount), 0)) as remaining_balance
            FROM loans l
            LEFT JOIN payments p ON l.loan_id = p.loan_id
            WHERE l.user_id = %s
            GROUP BY l.loan_id, l.amount
        """, (user_id,))
        
        loans = cur.fetchall()
        
        if not loans:
            print("\nYou don't have any loans.")
            return
        
        print(f"\n{'Loan ID':<8} {'Original Amt':<15} {'Remaining':<15}")
        print("-" * 40)
        for loan in loans:
            print(f"{loan[0]:<8} ${loan[1]:<14.2f} ${loan[2]:<14.2f}")
    except Exception as e:
        print(f"\nError checking balance: {e}")
    finally:
        if conn:
            conn.close()

def view_payment_history(user_id):
    print("\n=== Payment History ===")
    try:
        conn = get_db_connection()
        cur = conn.cursor()
        
        cur.execute("""
            SELECT p.payment_id, l.loan_id, p.amount, p.payment_date
            FROM payments p
            JOIN loans l ON p.loan_id = l.loan_id
            WHERE l.user_id = %s
            ORDER BY p.payment_date DESC
        """, (user_id,))
        
        payments = cur.fetchall()
        
        if not payments:
            print("\nNo payment history found.")
            return
        
        print(f"\n{'ID':<8} {'Loan ID':<10} {'Amount':<15} {'Date':<20}")
        print("-" * 60)
        for payment in payments:
            print(f"{payment[0]:<8} {payment[1]:<10} ${payment[2]:<14.2f} {payment[3].strftime('%Y-%m-%d %H:%M'):<20}")
    except Exception as e:
        print(f"\nError viewing payment history: {e}")
    finally:
        if conn:
            conn.close()

# Main menu
def main_menu(user_id):
    while True:
        print("\n=== Main Menu ===")
        print("1. Apply for a loan")
        print("2. Make a payment")
        print("3. Check balance")
        print("4. View payment history")
        print("5. Logout")
        
        choice = input("\nEnter your choice (1-5): ")
        
        if choice == '1':
            apply_for_loan(user_id)
        elif choice == '2':
            make_payment(user_id)
        elif choice == '3':
            check_balance(user_id)
        elif choice == '4':
            view_payment_history(user_id)
        elif choice == '5':
            print("\nLogged out successfully!")
            break
        else:
            print("\nInvalid choice. Please enter 1-5.")

# Main function
def main():
    print("\n=== Loan Application System ===")
    while True:
        user_id = login()
        
        if user_id:
            main_menu(user_id)
            
            print("\nWould you like to login again? (y/n)")
            choice = input().lower()
            if choice != 'y':
                print("\nThank you for using the Loan Application System!")
                break
        else:
            print("\nLogin failed. Would you like to try again? (y/n)")
            choice = input().lower()
            if choice != 'y':
                print("\nGoodbye!")
                break

if __name__ == "__main__":
    main()