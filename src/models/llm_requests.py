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
    rights: Rights
    priority: str = "Normal"
    props: Props
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
    query: str
    to: EmailStr
    cc: Optional[str] = ""
    subject: str
    text: str
    attachment: bool = True
    connection: str

class SendEmailLLMRequest(BaseLLMRequest):
    template: str = "110673709194435"
    variables: List[SendEmailVariables]

    def template_key(self) -> str:
        return "SENDEMAIL"

    def to_field_values(self) -> Dict[str, Any]:
        return {
            "template": self.template,
            "connection": self.variables.connection,
            "sql_query": self.variables.sql_query,
            "to": self.variables.to,
            "cc": self.variables.cc or "",
            "subject": self.variables.subject,
            "text": self.variables.text,
            "attachment": "true" if self.variables.attachment else "false",
        }


class SelectedColumn(BaseModel):
    columnName: str

class ReadSqlVariables(BaseModel):
    table_name: str
    query: str
    write_count: bool = False
    write_count_connection: str = ""
    execute_query: bool = True
    result_schema: str
    only_dataset_columns: bool = True
    write_count_table: str = ""
    drop_before_create: bool = False
    connection: str
    # columns: List[SelectedColumn] = Field(default_factory=list)


class ReadSqlLLMRequest(BaseLLMRequest):
    template: str = "2223045341865624"
    variables: List[ReadSqlVariables]

    def template_key(self) -> str:
        return "READSQL"

    def to_field_values(self) -> Dict[str, Any]:
        # Returns a list of dicts for each variable in variables
        return {
                "template": self.template,
                "table_name": self.variables.table_name,
                "query": self.variables.query,
                "write_count": self.variables.write_count,
                "write_count_connection": self.variables.write_count_connection,
                "execute_query": self.variables.execute_query,
                "result_schema": self.variables.result_schema,
                "only_dataset_columns": self.variables.only_dataset_columns,
                "write_count_table": self.variables.write_count_table,
                "drop_before_create": self.variables.drop_before_create,
                "connection": self.variables.connection,
            }




class ColumnSchema(BaseModel):
    columnName: str
    columnType: Optional[str] = None
    columnLength: Optional[int] = 2000
    alias: str = ""

class WriteDataVariables(BaseModel):
    only_dataset_columns: bool = True
    write_count_schemas: bool = False
    #add_columns: List[ColumnSchema] = Field(default_factory=list)
    #columns: List[ColumnSchema] = Field(default_factory=list)
    connection: str
    schemas: str
    data_set: str
    write_count: str
    write_count_connection: str
    drop_or_truncate: str
    table: str
    write_count_table: str = ""


class WriteDataLLMRequest(BaseLLMRequest):
    template: str = "28405918884279"
    variables: List[WriteDataVariables]

    def template_key(self) -> str:
        return "WRITEDATA"

    def to_field_values(self) -> Dict[str, Any]:
        # Returns a list of dicts for each variable in variables
        return {
                "template": self.template,
                "only_dataset_columns": self.variables.only_dataset_columns,
                "write_count_schemas": self.variables.write_count_schema,
                "connection": self.variables.connection,
                "schemas": self.variables.schemas,
                "data_set": self.variables.data_set,
                "write_count": self.variables.write_count,
                "write_count_connection": self.variables.write_count_connection,
                "drop_or_truncate": self.variables.drop_or_truncate,
                "table": self.variables.table,
                "write_count_table": self.variables.write_count_table,
            }
