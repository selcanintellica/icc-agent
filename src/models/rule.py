"""
Rule Models.

Data models for ICC Rule creation following the same patterns as natural_language.py
"""

from typing import Dict, List, Optional, Any
from dataclasses import dataclass, field
from pydantic import BaseModel, Field
import json

# Default folder ID for backward compatibility (same as in job_context.py)
DEFAULT_JOB_FOLDER = "3023602439587835"


class RuleNode(BaseModel):
    """
    Represents a node in a Rule flow.
    
    Node types:
    - Start: Entry point of the rule
    - Job: A job to execute (ReadSQL, WriteData, SendEmail, CompareSQL)
    - End: Exit point of the rule
    """
    id: int = Field(..., description="Unique node identifier (1-based)")
    x: int = Field(..., description="X coordinate for visual layout")
    y: int = Field(..., description="Y coordinate for visual layout")
    type: str = Field(..., description="Node type: Start, Job, or End")
    
    # Job-specific fields (only for type="Job")
    jobId: Optional[str] = Field(None, description="Job ID (only for Job nodes)")
    name: Optional[str] = Field(None, description="Node name (Job name or 'e1' for End)")
    description: Optional[str] = Field("", description="Node description")
    
    class Config:
        populate_by_name = True


class RuleDetail(BaseModel):
    """
    Contains the node and link structure of a Rule.
    
    This is serialized to JSON string in the final payload.
    """
    nodes: List[RuleNode] = Field(default_factory=list, description="List of nodes in the rule")
    links: Dict[str, List[int]] = Field(default_factory=dict, description="Node connections: {nodeId: [targetNodeIds]}")
    trueLinks: Dict[str, List[int]] = Field(default_factory=dict, description="Conditional true branches (empty for linear flows)")
    falseLinks: Dict[str, List[int]] = Field(default_factory=dict, description="Conditional false branches (empty for linear flows)")
    errorRaise: str = Field("", description="Error handling configuration")
    
    def to_json_string(self) -> str:
        """Convert to JSON string for the payload, excluding null values."""
        # Exclude None values to match expected API format
        data = self.model_dump(exclude_none=True)
        # Also need to handle nodes - each node should exclude its None values
        if 'nodes' in data:
            clean_nodes = []
            for node in data['nodes']:
                clean_node = {k: v for k, v in node.items() if v is not None}
                clean_nodes.append(clean_node)
            data['nodes'] = clean_nodes
        return json.dumps(data, separators=(',', ':'))


class RuleProps(BaseModel):
    """Rule properties."""
    active: str = Field("true", description="Whether the rule is active")
    description: str = Field("", description="Rule description")
    name: str = Field(..., description="Rule name")


class RuleRights(BaseModel):
    """Rule access rights."""
    owner: str = Field("184431757886694", description="Owner ID")


class RulePayload(BaseModel):
    """
    Complete Rule payload for the /rule/save API endpoint.
    
    Example payload:
    {
        "detail": "{\"nodes\":[...],\"links\":{...},\"trueLinks\":{},\"falseLinks\":{},\"errorRaise\":\"\"}",
        "folder": "3023602439587835",
        "image": "",
        "props": {"active": "true", "description": "", "name": "MyRule"},
        "rights": {"owner": "184431757886694"},
        "raiseError": "false"
    }
    """
    detail: str = Field(..., description="JSON string of RuleDetail")
    folder: str = Field(..., description="Folder ID where to save the rule")
    image: str = Field("", description="Base64 image (can be empty)")
    props: RuleProps = Field(..., description="Rule properties including name")
    rights: RuleRights = Field(default_factory=RuleRights, description="Access rights")
    raiseError: str = Field("false", description="Whether to raise errors")
    
    def to_api_payload(self) -> Dict[str, Any]:
        """Convert to dictionary for API request."""
        return {
            "detail": self.detail,
            "folder": self.folder,
            "image": self.image,
            "props": self.props.model_dump(),
            "rights": self.rights.model_dump(),
            "raiseError": self.raiseError
        }


@dataclass
class CreatedJob:
    """
    Represents a job created during the chat session.
    
    Used for tracking jobs that can be combined into a rule.
    """
    id: str
    name: str
    type: str  # read_sql, write_data, send_email, compare_sql
    folder: str = DEFAULT_JOB_FOLDER
    
    def to_dict(self) -> Dict[str, str]:
        """Convert to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "type": self.type,
            "folder": self.folder
        }


class RuleBuilder:
    """
    Builder for creating Rule payloads from a list of jobs.
    
    Handles:
    - Node position calculation for linear flows
    - Link generation based on job order
    - Payload assembly
    """
    
    # Layout constants
    START_X = 100
    START_Y = 180
    NODE_X_INCREMENT = 220
    END_NAME = "e1"
    
    @classmethod
    def build(
        cls,
        jobs: List[Dict[str, str]],
        folder_id: str,
        rule_name: str,
        description: str = ""
    ) -> RulePayload:
        """
        Build a rule payload from a list of jobs.
        
        Args:
            jobs: List of job dictionaries with id, name, type, folder
            folder_id: Folder ID to save the rule
            rule_name: Name for the rule
            description: Optional rule description
            
        Returns:
            RulePayload: Ready to send to API
            
        Raises:
            ValueError: If jobs list is empty, has less than 2 jobs, or has jobs with missing IDs
        """
        if not jobs:
            raise ValueError("Cannot create rule with no jobs")
        if len(jobs) < 2:
            raise ValueError("Rule requires at least 2 jobs")
        
        # Validate all jobs have valid IDs
        jobs_without_ids = [job.get("name", "unknown") for job in jobs if not job.get("id")]
        if jobs_without_ids:
            raise ValueError(f"Cannot create rule: the following jobs are missing IDs: {', '.join(jobs_without_ids)}")
        
        # Build nodes
        nodes = cls._build_nodes(jobs)
        
        # Build links
        links = cls._build_links(len(jobs))
        
        # Create detail
        detail = RuleDetail(
            nodes=nodes,
            links=links,
            trueLinks={},
            falseLinks={},
            errorRaise=""
        )
        
        # Create payload
        return RulePayload(
            detail=detail.to_json_string(),
            folder=folder_id,
            image="",
            props=RuleProps(
                active="true",
                description=description,
                name=rule_name
            ),
            rights=RuleRights(owner="184431757886694"),
            raiseError="false"
        )
    
    @classmethod
    def _build_nodes(cls, jobs: List[Dict[str, str]]) -> List[RuleNode]:
        """
        Build node list with Start, Job nodes, and End.
        
        Layout: Start -> Job1 -> Job2 -> ... -> JobN -> End
        
        Node format matches ICC UI:
        - Start: {id, x, y, type}
        - Job: {id, x, y, type, jobId, name, description}
        - End: {id, x, y, type, name}
        """
        nodes = []
        current_id = 1
        current_x = cls.START_X
        
        # Start node - minimal fields
        nodes.append(RuleNode(
            id=current_id,
            x=current_x,
            y=cls.START_Y,
            type="Start",
            description=None  # Will be excluded from JSON
        ))
        current_id += 1
        current_x += cls.NODE_X_INCREMENT
        
        # Job nodes - include all fields
        for job in jobs:
            nodes.append(RuleNode(
                id=current_id,
                x=current_x,
                y=cls.START_Y,
                type="Job",
                jobId=job["id"],
                name=job["name"],
                description=""
            ))
            current_id += 1
            current_x += cls.NODE_X_INCREMENT
        
        # End node - include name but not description
        nodes.append(RuleNode(
            id=current_id,
            x=current_x,
            y=cls.START_Y,
            type="End",
            name=cls.END_NAME,
            description=None  # Will be excluded from JSON
        ))
        
        return nodes
    
    @classmethod
    def _build_links(cls, job_count: int) -> Dict[str, List[int]]:
        """
        Build link dictionary for linear flow.
        
        Links: 1 -> 2 -> 3 -> ... -> n+2
        (Start=1, Jobs=2..n+1, End=n+2)
        """
        links = {}
        total_nodes = job_count + 2  # Start + Jobs + End
        
        for i in range(1, total_nodes):
            links[str(i)] = [i + 1]
        
        return links
    
    @classmethod
    def format_flow_description(cls, jobs: List[Dict[str, str]]) -> str:
        """
        Format a human-readable description of the rule flow.
        
        Args:
            jobs: List of job dictionaries
            
        Returns:
            String like "Start -> read_job -> email_job -> End"
        """
        if not jobs:
            return "Empty flow"
        
        parts = ["Start"]
        for job in jobs:
            parts.append(job["name"])
        parts.append("End")
        
        return " -> ".join(parts)

