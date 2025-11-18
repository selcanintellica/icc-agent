# Schema Documentation

This folder contains database schema documentation organized by connection and schema.

## Structure

```
schema_docs/
├── {connection}/       <- Database connection name
│   └── {schema}/       <- Schema name
│       └── {table}.txt <- Table definition file
```

## Quick Start

### 1. Add Your Connection

Create a folder with your connection name:
```bash
mkdir schema_docs/your_connection_name
```

### 2. Add Your Schema

Create a subfolder for your schema:
```bash
mkdir schema_docs/your_connection_name/YOUR_SCHEMA
```

### 3. Add Your Tables

Create a `.txt` file for each table following this template:

```
Table: table_name
Schema: SCHEMA_NAME
Connection: connection_name

Description:
What this table stores.

Columns:
- column_name (DATA_TYPE, constraints): Description
- another_column (DATA_TYPE): Description

Indexes:
- INDEX_NAME on column_name

Foreign Keys:
- FK_NAME: column → other_table.other_column

Related Tables:
- related_table (relationship)

Example Queries:
-- Example query description
SELECT * FROM table_name WHERE ...;
```

## Examples

See the existing files:
- `oracle_10/SALES/customers.txt` - Full customer table example
- `oracle_10/SALES/orders.txt` - Table with foreign keys
- `oracle_10/HR/employees.txt` - Self-referencing table

## Best Practices

✅ **DO:**
- Use exact data types from your database
- Include ALL columns with descriptions
- Document foreign keys and relationships
- Add example queries
- Keep files updated when schema changes

❌ **DON'T:**
- Include actual data or sensitive information
- Use generic data types like "TEXT" instead of "VARCHAR2(100)"
- Forget to document constraints (NOT NULL, UNIQUE, etc.)
- Leave out foreign keys

## Need Help?

See the full documentation: `docs/SCHEMA_DOCS_GUIDE.md`

## Current Connections

<!-- Update this list as you add connections -->

- **oracle_10** - Oracle Production Database
  - SALES - Sales and customer data
  - HR - Human resources and employee data
  
- **oracle_dev** - Oracle Development Database
  - TEST_SCHEMA - Test data
  
- **postgres_prod** - PostgreSQL Production
  - PUBLIC - Main schema

---

**Note**: Files in this folder are automatically discovered by the system. No configuration needed!
