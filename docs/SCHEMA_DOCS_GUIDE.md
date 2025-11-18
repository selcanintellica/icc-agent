# Schema Documentation System

## Overview

This system uses a file-based approach to manage database schema documentation. Users select a connection, schema, and tables through the UI, and the SQL generation agent dynamically loads the relevant table definitions from files.

## Folder Structure

```
schema_docs/
├── {connection_name}/
│   ├── {schema_name}/
│   │   ├── {table_name}.txt
│   │   ├── {table_name}.txt
│   │   └── ...
│   └── {another_schema}/
│       └── ...
└── {another_connection}/
    └── ...
```

### Example Structure

```
schema_docs/
├── oracle_10/
│   ├── SALES/
│   │   ├── customers.txt
│   │   ├── orders.txt
│   │   ├── products.txt
│   │   └── order_items.txt
│   └── HR/
│       ├── employees.txt
│       └── departments.txt
├── oracle_dev/
│   └── TEST_SCHEMA/
│       └── test_data.txt
└── postgres_prod/
    └── PUBLIC/
        ├── sales.txt
        └── inventory.txt
```

## How It Works

### 1. User Workflow

1. **Select Connection**: User chooses a database connection (e.g., `oracle_10`)
2. **Select Schema**: Dropdown updates to show available schemas (e.g., `SALES`, `HR`)
3. **Select Tables**: User selects one or more tables (e.g., `customers`, `orders`)
4. **Chat with Agent**: User asks natural language questions about the data

### 2. Behind the Scenes

1. **Schema Discovery**: The `SchemaLoader` scans the `schema_docs` folder to discover available connections, schemas, and tables
2. **Dynamic Loading**: When user asks a question, the SQL agent loads the selected table definition files
3. **Context Building**: Table definitions are combined and injected into the LLM prompt
4. **SQL Generation**: LLM generates SQL using only the provided table definitions

## Table Definition File Format

Each table should have its own `.txt` file with the following structure:

```
Table: {table_name}
Schema: {schema_name}
Connection: {connection_name}

Description:
Brief description of what this table stores and its purpose.

Columns:
- column_name (DATA_TYPE, constraints): Description of the column
- column_name (DATA_TYPE, constraints): Description of the column
...

Indexes:
- INDEX_NAME on column_name
...

Foreign Keys:
- FK_NAME: column → other_table.other_column
...

Related Tables:
- table_name (relationship description)
...

Example Queries:
-- Example 1: Description
SELECT ...;

-- Example 2: Description
SELECT ...;
```

### Example Table Definition

See `schema_docs/oracle_10/SALES/customers.txt` for a complete example:

```
Table: customers
Schema: SALES
Connection: oracle_10

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
- status (VARCHAR2(20), DEFAULT 'active'): Customer status

Indexes:
- PK_CUSTOMERS on customer_id
- IDX_CUSTOMER_EMAIL on email

Foreign Keys:
None

Related Tables:
- orders (customer_id)

Example Queries:
-- Get all active customers from USA
SELECT * FROM customers WHERE country = 'USA' AND status = 'active';
```

## Adding New Connections/Schemas/Tables

### Adding a New Connection

1. Create a folder under `schema_docs/` with your connection name:
   ```
   schema_docs/my_new_connection/
   ```

2. The connection will automatically appear in the UI dropdown

### Adding a New Schema

1. Create a folder under your connection with the schema name:
   ```
   schema_docs/my_connection/MY_SCHEMA/
   ```

2. The schema will automatically appear in the UI when the connection is selected

### Adding a New Table

1. Create a `.txt` file in the schema folder with the table name:
   ```
   schema_docs/my_connection/MY_SCHEMA/my_table.txt
   ```

2. Follow the table definition format (see above)

3. The table will automatically appear in the UI when the schema is selected

4. **Important**: Include detailed information:
   - All columns with data types and constraints
   - Indexes for performance optimization
   - Foreign keys for relationships
   - Example queries to guide the LLM

## Best Practices

### 1. Naming Conventions

- **Connections**: Use lowercase with underscores (e.g., `oracle_prod`, `mysql_dev`)
- **Schemas**: Use UPPERCASE (e.g., `SALES`, `HR`, `PUBLIC`)
- **Tables**: Use lowercase (e.g., `customers`, `order_items`)
- **Files**: Use lowercase `.txt` extension (e.g., `customers.txt`)

### 2. Table Documentation

- **Be Specific**: Include exact data types (e.g., `VARCHAR2(100)` not just `VARCHAR`)
- **Add Constraints**: Document `NOT NULL`, `UNIQUE`, `PRIMARY KEY`, etc.
- **Explain Relationships**: List all foreign keys and related tables
- **Provide Examples**: Include 2-3 example queries showing common use cases
- **Describe Purpose**: Explain what the table stores and why

### 3. Maintenance

- **Keep Updated**: When schema changes, update the corresponding `.txt` file
- **Version Control**: Commit schema docs to git for change tracking
- **Review Regularly**: Ensure documentation matches actual database schema

### 4. Security

- **No Sensitive Data**: Don't include actual data values in documentation
- **No Credentials**: Never put passwords or connection strings in these files
- **Generic Examples**: Use placeholder values in example queries

## Architecture Components

### 1. SchemaLoader (`src/utils/schema_loader.py`)

- Scans `schema_docs/` folder structure
- Discovers available connections, schemas, and tables
- Loads table definition files
- Provides options for UI dropdowns

### 2. Memory (`src/ai/router/memory.py`)

- Stores selected connection, schema, and tables
- Persists across conversation turns
- Used by router to pass context to SQL agent

### 3. SQL Agent (`src/ai/router/sql_agent.py`)

- Receives user's natural language query
- Loads table definitions for selected tables
- Builds LLM prompt with schema context
- Generates SQL query using only provided tables

### 4. App UI (`app.py`)

- Cascade dropdowns: Connection → Schema → Tables
- Auto-updates based on selections
- Validates configuration before allowing queries

## Troubleshooting

### Tables Not Appearing in UI

1. Check file extension is `.txt`
2. Verify folder structure matches pattern
3. Check console logs for schema loader warnings
4. Restart the app to refresh schema cache

### SQL Agent Not Using Correct Schema

1. Verify table definition file exists
2. Check file content is properly formatted
3. Look for errors in logs during file loading
3. Ensure connection/schema/tables are selected in UI

### LLM Generating Invalid SQL

1. Add more detailed column descriptions
2. Include more example queries in table definitions
3. Verify foreign key relationships are documented
4. Check that data types are database-specific (Oracle, PostgreSQL, etc.)

## Example: Adding a Complete Connection

Let's add a new MySQL connection with a `store` schema:

```bash
# 1. Create connection folder
mkdir schema_docs/mysql_store

# 2. Create schema folder
mkdir schema_docs/mysql_store/store

# 3. Create table files
touch schema_docs/mysql_store/store/items.txt
touch schema_docs/mysql_store/store/inventory.txt
```

Now edit `items.txt`:

```
Table: items
Schema: store
Connection: mysql_store

Description:
Store inventory items with pricing and stock information.

Columns:
- item_id (INT, Primary Key, AUTO_INCREMENT): Unique item identifier
- item_name (VARCHAR(100), NOT NULL): Product name
- category (VARCHAR(50)): Product category
- price (DECIMAL(10,2), NOT NULL): Current price
- stock_qty (INT, DEFAULT 0): Quantity in stock
- created_at (TIMESTAMP, DEFAULT CURRENT_TIMESTAMP): Record creation time

Indexes:
- PRIMARY KEY on item_id
- INDEX idx_category on category

Foreign Keys:
None

Related Tables:
- inventory (item_id)

Example Queries:
-- Get all items in Electronics category
SELECT * FROM items WHERE category = 'Electronics';

-- Find low stock items
SELECT item_name, stock_qty FROM items WHERE stock_qty < 10;
```

4. Restart the app - the new connection will appear!

## Integration Points

### For Developers

If you need to extend this system:

1. **Custom Schema Sources**: Modify `SchemaLoader` to load from databases or APIs
2. **Schema Validation**: Add validation in `SchemaLoader.load_table_definition()`
3. **Caching**: Add Redis caching for frequently accessed schemas
4. **Auto-Generation**: Create scripts to generate `.txt` files from live databases

### API Example

```python
from src.utils.schema_loader import get_schema_loader

# Get schema loader
loader = get_schema_loader()

# Discover structure
connections = loader.get_available_connections()
schemas = loader.get_schemas_for_connection("oracle_10")
tables = loader.get_tables_for_schema("oracle_10", "SALES")

# Load definitions
table_def = loader.load_table_definition("oracle_10", "SALES", "customers")
multiple_defs = loader.load_multiple_tables("oracle_10", "SALES", ["customers", "orders"])

# Get full structure
structure = loader.get_connection_structure()
# Returns: {"oracle_10": {"SALES": ["customers", "orders", ...], "HR": [...]}, ...}
```

## Future Enhancements

- **Auto-sync**: Automatically sync from database catalogs
- **Version History**: Track schema changes over time
- **Search**: Full-text search across all table definitions
- **Validation**: Check that table definitions match actual database
- **Templates**: Pre-built templates for common database types
- **Documentation UI**: Web interface to edit table definitions
