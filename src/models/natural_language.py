import uuid
from typing import List, Optional, Any, Dict
from pydantic import BaseModel, Field, EmailStr


class Rights(BaseModel):
    owner: str = "184431757886694"

class Props(BaseModel):
    active: str = "true"
    name: str
    description: Optional[str] = ""

class BaseLLMRequest(BaseModel):
    id: Optional[str] = None
    rights: Dict[str, Any] = Field(default_factory=lambda: {"owner": "184431757886694"})
    priority: str = "Normal"
    props: Dict[str, Any] = Field(default_factory=dict)
    skip: str = "false"
    folder: str = "3023602439587835"

    def ensure_id(self):
        if not self.id:
            self.id = str(uuid.uuid4())

    def template_key(self) -> str:
        raise NotImplementedError

    def to_field_values(self) -> Dict[str, Any]:
        raise NotImplementedError


class SendEmailVariables(BaseModel):
    query: Optional[str] = Field(
        None,
        description="SQL query to execute and fetch data for the email. Optional - can be omitted if sending static content.",
        field_id="110673709444744"
    )
    to: Optional[EmailStr] = Field(
        None,
        description="Primary recipient email address. Can be a single email or comma-separated list.",
        field_id="110673709461441"
    )
    cc: Optional[str] = Field(
        None,
        description="Carbon copy recipient email addresses. Comma-separated list of emails.",
        field_id="110673709490605"
    )
    subject: Optional[str] = Field(
        None,
        description="Email subject line. Brief description of the email content.",
        field_id="110673709380478"
    )
    text: Optional[str] = Field(
        None,
        description="Email body text. Main message content to be sent in the email.",
        field_id="110673709424784"
    )
    attachment: Optional[bool] = Field(
        True,
        description="Whether to attach query results as a file. True to include attachment, False for inline only.",
        field_id="1600766934"
    )
    connection: Optional[str] = Field(
        None,
        description="Database connection identifier to use for executing the query.",
        field_id="110673709476681"
    )

class SendEmailLLMRequest(BaseLLMRequest):
    template: str = "110673709194435"
    variables: List[SendEmailVariables]

    def template_key(self) -> str:
        return "SENDEMAIL"

    def to_field_values(self) -> Dict[str, Any]:
        # Access first variable since it's a list
        var = self.variables[0]
        return {
            "template": self.template,
            "connection": var.connection,
            "query": var.query,
            "to": var.to,
            "cc": var.cc or "",
            "subject": var.subject,
            "text": var.text,
            "attachment": "true" if var.attachment else "false",
        }


class SelectedColumn(BaseModel):
    columnName: str

class ReadSqlVariables(BaseModel):
    # REQUIRED FIELDS
    query: str = Field(
        ...,
        description="SQL query to execute. Must be a valid SQL statement (SELECT, INSERT, UPDATE, etc.). The query results and column schema can be used as input for a subsequent write_data_job.",
        field_id="2223045341935949"
    )
    connection: str = Field(
        ...,
        description="Database connection identifier. Required to establish database connection for query execution.",
        field_id="2223045341969932"
    )
    
    # OPTIONAL FIELDS
    table_name: Optional[str] = Field(
        None,
        description="Target table name where results will be written. Optional - only needed if storing query results.",
        field_id="284961720524"
    )
    write_count: Optional[bool] = Field(
        False,
        description="Whether to write the row count of the query results. False by default.",
        field_id="28405919373737"
    )
    write_count_connection: Optional[str] = Field(
        None,
        description="Connection identifier for writing row count. Only needed if write_count is True.",
        field_id="28405919100373"
    )
    execute_query: Optional[bool] = Field(
        True,
        description="Whether to execute the query immediately. True by default. Set False to validate only.",
        field_id="28405919526172"
    )
    result_schema: Optional[str] = Field(
        None,
        description="Schema name for the result table. Optional - used to organize tables in databases.",
        field_id="284961720523"
    )
    only_dataset_columns: Optional[bool] = Field(
        True,
        description="Whether to include only columns from the dataset. True limits to dataset columns only.",
        field_id="284961720526"
    )
    write_count_table: Optional[str] = Field(
        None,
        description="Table name where row count will be written. Only needed if write_count is True.",
        field_id="28405919059373"
    )
    drop_before_create: Optional[bool] = Field(
        False,
        description="Whether to drop the existing table before creating a new one. False preserves existing data.",
        field_id="284961720525"
    )


class ReadSqlLLMRequest(BaseLLMRequest):
    """
    Request model for Read SQL job.
    
    BUSINESS RULE: This job can be chained with write_data_job.
    The response from this job includes:
    - Job ID (object_id): Used as the data_set parameter in write_data_job
    - Column information: Used to populate the columns parameter in write_data_job
    
    Workflow: read_sql_job → get response (job_id, columns) → write_data_job(data_set=job_id, columns=columns)
    """
    template: str = "2223045341865624"
    variables: List[ReadSqlVariables]

    def template_key(self) -> str:
        return "READSQL"

    def to_field_values(self) -> Dict[str, Any]:
        # Access first variable since it's a list
        var = self.variables[0]
        return {
                "template": self.template,
                "table_name": var.table_name,
                "query": var.query,
                "write_count": var.write_count,
                "write_count_connection": var.write_count_connection,
                "execute_query": var.execute_query,
                "result_schema": var.result_schema,
                "only_dataset_columns": var.only_dataset_columns,
                "write_count_table": var.write_count_table,
                "drop_before_create": var.drop_before_create,
                "connection": var.connection,
            }




class ColumnSchema(BaseModel):
    columnName: str = Field(..., description="Name of the column")
    columnType: Optional[str] = Field(None, description="Data type of the column (e.g., VARCHAR, INT, DATE)")
    columnLength: Optional[int] = Field(2000, description="Maximum length for the column, default 2000")
    alias: Optional[str] = Field("", description="Alias name for the column")

class WriteDataVariables(BaseModel):
    # REQUIRED FIELDS
    only_dataset_columns: bool = Field(
        ...,
        description="Whether to write only columns present in the dataset. True restricts to dataset columns only.",
        field_id="28405919100737"
    )
    connection: str = Field(
        ...,
        description="Database connection identifier. Required to establish connection for writing data.",
        field_id="28405919100547"
    )
    data_set: str = Field(
        ...,
        description="Dataset identifier containing the data to write. IMPORTANT: This should be the job ID (object_id) returned from a previously executed read_sql_job.",
        field_id="28405919074002"
    )
    drop_or_truncate: str = Field(
        ...,
        description="Strategy for existing table: 'drop' to remove and recreate, 'truncate' to clear data only, 'none' to append.",
        field_id="28405919008625"
    )
    columns: List[ColumnSchema] = Field(
        ...,
        description="List of column definitions for the target table. IMPORTANT: These columns should match the columns from the read_sql_job results that produced the data_set.",
        field_id="28405919027068"
    )
    table: str = Field(
        ...,
        description="Target table name where data will be written. Must be a valid table name.",
        field_id="28405919059935"
    )
    
    # OPTIONAL FIELDS
    write_count_schemas: Optional[bool] = Field(
        False,
        description="Whether to write count information to schemas. False by default.",
        field_id="28405919284178"
    )
    add_columns: Optional[List[ColumnSchema]] = Field(
        default_factory=list,
        description="Additional columns to add to the table beyond dataset columns. Empty list by default.",
        field_id="28405918976213"
    )
    schemas: Optional[str] = Field(
        None,
        description="Schema name for organizing the table. Optional database schema identifier.",
        field_id="28405919042037"
    )
    write_count: Optional[str] = Field(
        None,
        description="Whether to write row count after data write. Specify 'true' or 'false'.",
        field_id="28405919839465"
    )
    write_count_connection: Optional[str] = Field(
        None,
        description="Connection identifier for writing row count. Only needed if write_count is enabled.",
        field_id="28405919193743"
    )
    write_count_table: Optional[str] = Field(
        None,
        description="Table name where row count will be written. Only needed if write_count is enabled.",
        field_id="28405919372169"
    )


class WriteDataLLMRequest(BaseLLMRequest):
    """
    Request model for Write Data job.
    
    BUSINESS RULE: This job is typically used AFTER a read_sql_job to write the query results to a table.
    
    Workflow:
    1. Execute read_sql_job to get query results
    2. Extract job_id (object_id) and columns from the read_sql response
    3. Use write_data_job with:
       - data_set = job_id from read_sql response
       - columns = column schema from read_sql results
    
    This creates a data pipeline: SQL Query → Read Results → Write to Target Table
    """
    template: str = "28405918884279"
    variables: List[WriteDataVariables]

    def template_key(self) -> str:
        return "WRITEDATA"

    def to_field_values(self) -> Dict[str, Any]:
        # Access first variable since it's a list
        var = self.variables[0]
        return {
                "template": self.template,
                "only_dataset_columns": var.only_dataset_columns,
                "write_count_schemas": var.write_count_schemas,
                "connection": var.connection,
                "schemas": var.schemas,
                "data_set": var.data_set,
                "write_count": var.write_count,
                "write_count_connection": var.write_count_connection,
                "drop_or_truncate": var.drop_or_truncate,
                "table": var.table,
                "write_count_table": var.write_count_table,
            }
