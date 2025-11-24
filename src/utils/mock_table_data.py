"""
Mock table definitions for testing when TABLE_API_MOCK=true.
This data simulates API responses for table definitions.
"""

from typing import Dict, Optional

# Mock table definitions organized by connection -> schema -> table
MOCK_TABLE_DEFINITIONS: Dict[str, Dict[str, Dict[str, str]]] = {
    "ORACLE_10": {
        "SALES": {
            "customers": """Table: customers
Schema: SALES
Connection: ORACLE_10

Description:
Stores customer information including contact details and addresses.

Columns:
- customer_id (NUMBER, Primary Key): Unique identifier for each customer
- first_name (VARCHAR2(50), NOT NULL): Customer's first name
- last_name (VARCHAR2(50), NOT NULL): Customer's last name
- email (VARCHAR2(100), UNIQUE): Customer's email address
- phone (VARCHAR2(20)): Contact phone number
- country (VARCHAR2(50)): Country of residence
- city (VARCHAR2(50)): City of residence
- address (VARCHAR2(200)): Street address
- created_date (DATE, DEFAULT SYSDATE): Account creation date
- status (VARCHAR2(20), DEFAULT 'active'): Customer status (active, inactive, suspended)

Indexes:
- PK_CUSTOMERS on customer_id
- IDX_CUSTOMER_EMAIL on email
- IDX_CUSTOMER_COUNTRY on country

Foreign Keys:
None

Related Tables:
- orders (customer_id)

Example Queries:
-- Get all active customers from USA
SELECT * FROM customers WHERE country = 'USA' AND status = 'active';

-- Find customer by email
SELECT * FROM customers WHERE email = 'john.doe@example.com';
""",
            "orders": """Table: orders
Schema: SALES
Connection: ORACLE_10

Description:
Stores order information including customer, dates, and order status.

Columns:
- order_id (NUMBER, Primary Key): Unique identifier for each order
- customer_id (NUMBER, NOT NULL): Reference to customer who placed the order
- order_date (DATE, DEFAULT SYSDATE): Date when order was placed
- status (VARCHAR2(20), DEFAULT 'pending'): Order status (pending, processing, shipped, delivered, cancelled)
- total_amount (NUMBER(10,2)): Total order amount
- shipping_address (VARCHAR2(200)): Shipping address
- payment_method (VARCHAR2(50)): Payment method used
- notes (VARCHAR2(500)): Additional order notes

Indexes:
- PK_ORDERS on order_id
- IDX_ORDERS_CUSTOMER on customer_id
- IDX_ORDERS_DATE on order_date
- IDX_ORDERS_STATUS on status

Foreign Keys:
- FK_ORDERS_CUSTOMER: customer_id → customers.customer_id

Related Tables:
- customers (customer_id)
- order_items (order_id)

Example Queries:
-- Get all orders for a specific customer
SELECT * FROM orders WHERE customer_id = 123;

-- Find pending orders
SELECT * FROM orders WHERE status = 'pending' ORDER BY order_date DESC;
""",
            "order_items": """Table: order_items
Schema: SALES
Connection: ORACLE_10

Description:
Stores individual items within each order.

Columns:
- order_item_id (NUMBER, Primary Key): Unique identifier for each order item
- order_id (NUMBER, NOT NULL): Reference to the order
- product_id (NUMBER, NOT NULL): Reference to the product
- quantity (NUMBER, NOT NULL): Quantity ordered
- unit_price (NUMBER(10,2), NOT NULL): Price per unit at time of order
- discount (NUMBER(5,2), DEFAULT 0): Discount percentage applied
- line_total (NUMBER(10,2)): Total for this line item

Indexes:
- PK_ORDER_ITEMS on order_item_id
- IDX_ORDER_ITEMS_ORDER on order_id
- IDX_ORDER_ITEMS_PRODUCT on product_id

Foreign Keys:
- FK_ORDER_ITEMS_ORDER: order_id → orders.order_id
- FK_ORDER_ITEMS_PRODUCT: product_id → products.product_id

Related Tables:
- orders (order_id)
- products (product_id)

Example Queries:
-- Get all items for a specific order
SELECT * FROM order_items WHERE order_id = 456;

-- Calculate total for an order
SELECT SUM(line_total) FROM order_items WHERE order_id = 456;
""",
            "products": """Table: products
Schema: SALES
Connection: ORACLE_10

Description:
Stores product catalog information.

Columns:
- product_id (NUMBER, Primary Key): Unique identifier for each product
- product_name (VARCHAR2(100), NOT NULL): Product name
- category (VARCHAR2(50)): Product category
- description (VARCHAR2(500)): Product description
- price (NUMBER(10,2), NOT NULL): Current price
- stock_quantity (NUMBER, DEFAULT 0): Available stock quantity
- reorder_level (NUMBER, DEFAULT 10): Minimum stock level before reorder
- supplier (VARCHAR2(100)): Supplier name
- active (CHAR(1), DEFAULT 'Y'): Product is active (Y/N)

Indexes:
- PK_PRODUCTS on product_id
- IDX_PRODUCTS_CATEGORY on category
- IDX_PRODUCTS_NAME on product_name

Foreign Keys:
None

Related Tables:
- order_items (product_id)

Example Queries:
-- Get all active products in Electronics category
SELECT * FROM products WHERE category = 'Electronics' AND active = 'Y';

-- Find products needing reorder
SELECT * FROM products WHERE stock_quantity <= reorder_level;
"""
        },
        "HR": {
            "employees": """Table: employees
Schema: HR
Connection: ORACLE_10

Description:
Stores employee information including personal details and job assignments.

Columns:
- employee_id (NUMBER, Primary Key): Unique identifier for each employee
- first_name (VARCHAR2(50), NOT NULL): Employee's first name
- last_name (VARCHAR2(50), NOT NULL): Employee's last name
- email (VARCHAR2(100), UNIQUE): Employee's email address
- phone (VARCHAR2(20)): Contact phone number
- hire_date (DATE, NOT NULL): Date employee was hired
- job_title (VARCHAR2(50)): Current job title
- department_id (NUMBER): Reference to department
- manager_id (NUMBER): Reference to manager (self-referencing)
- salary (NUMBER(10,2)): Current salary
- status (VARCHAR2(20), DEFAULT 'active'): Employment status

Indexes:
- PK_EMPLOYEES on employee_id
- IDX_EMPLOYEES_DEPT on department_id
- IDX_EMPLOYEES_MANAGER on manager_id
- IDX_EMPLOYEES_EMAIL on email

Foreign Keys:
- FK_EMPLOYEES_DEPT: department_id → departments.department_id
- FK_EMPLOYEES_MANAGER: manager_id → employees.employee_id

Related Tables:
- departments (department_id)
- employees (manager_id, self-referencing)

Example Queries:
-- Get all employees in a department
SELECT * FROM employees WHERE department_id = 10;

-- Find employees reporting to a specific manager
SELECT * FROM employees WHERE manager_id = 100;
""",
            "departments": """Table: departments
Schema: HR
Connection: ORACLE_10

Description:
Stores department information.

Columns:
- department_id (NUMBER, Primary Key): Unique identifier for each department
- department_name (VARCHAR2(50), NOT NULL, UNIQUE): Department name
- manager_id (NUMBER): Department manager (reference to employees)
- location (VARCHAR2(50)): Department location
- budget (NUMBER(12,2)): Department budget

Indexes:
- PK_DEPARTMENTS on department_id
- UK_DEPT_NAME on department_name
- IDX_DEPT_MANAGER on manager_id

Foreign Keys:
- FK_DEPARTMENTS_MANAGER: manager_id → employees.employee_id

Related Tables:
- employees (department_id, manager_id)

Example Queries:
-- Get all departments
SELECT * FROM departments ORDER BY department_name;

-- Find department with specific manager
SELECT * FROM departments WHERE manager_id = 100;
"""
        }
    },
    "POSTGRE_11": {
        "PUBLIC": {
            "users": """Table: users
Schema: PUBLIC
Connection: POSTGRE_11

Description:
Stores user account information.

Columns:
- user_id (SERIAL, Primary Key): Unique identifier for each user
- username (VARCHAR(50), NOT NULL, UNIQUE): Username
- email (VARCHAR(100), NOT NULL, UNIQUE): Email address
- password_hash (VARCHAR(255), NOT NULL): Hashed password
- created_at (TIMESTAMP, DEFAULT NOW()): Account creation timestamp
- last_login (TIMESTAMP): Last login timestamp
- is_active (BOOLEAN, DEFAULT TRUE): Account is active

Indexes:
- PK_USERS on user_id
- UK_USERS_USERNAME on username
- UK_USERS_EMAIL on email

Foreign Keys:
None

Related Tables:
- user_sessions (user_id)

Example Queries:
-- Get active users
SELECT * FROM users WHERE is_active = TRUE;

-- Find user by email
SELECT * FROM users WHERE email = 'user@example.com';
"""
        }
    }
}


def get_mock_table_definition(connection: str, schema: str, table: str) -> Optional[str]:
    """
    Get mock table definition.
    
    Args:
        connection: Connection name
        schema: Schema name
        table: Table name
        
    Returns:
        Table definition string or None if not found
    """
    try:
        return MOCK_TABLE_DEFINITIONS[connection][schema][table]
    except KeyError:
        return None
