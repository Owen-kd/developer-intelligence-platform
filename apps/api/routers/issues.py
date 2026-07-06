"""이슈 리포트 라우터. 얇게 유지하고 조회는 컨테이너 저장소에 위임한다."""

from __future__ import annotations

from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel

from apps.api.dependencies.auth import require_principal
from apps.api.dependencies.container import get_container
from apps.composition import DipInMemoryApp

router = APIRouter(
    prefix="/issues",
    tags=["issues"],
    dependencies=[Depends(require_principal)],
)

Container = Annotated[DipInMemoryApp, Depends(get_container)]


class IssueSummary(BaseModel):
    jira_key: str
    summary: str
    status: str
    priority: str


class KnowledgeView(BaseModel):
    id: str
    type: str
    summary: str
    sources: list[str]


class IssueDetail(IssueSummary):
    knowledge: list[KnowledgeView]


@router.get("", response_model=list[IssueSummary])
async def list_issues(container: Container) -> list[IssueSummary]:
    issues = await container.issue_repo.list_issues()
    return [
        IssueSummary(
            jira_key=issue.jira_key,
            summary=issue.summary,
            status=issue.status,
            priority=issue.priority,
        )
        for issue in issues
    ]


@router.get("/{jira_key}", response_model=IssueDetail)
async def get_issue(jira_key: str, container: Container) -> IssueDetail:
    issue = await container.issue_repo.get_issue(jira_key)
    if issue is None or issue.id is None:
        raise HTTPException(status_code=404, detail=f"이슈를 찾을 수 없다: {jira_key}")

    knowledge = await container.knowledge_repo.list_by_issue(issue.id)
    return IssueDetail(
        jira_key=issue.jira_key,
        summary=issue.summary,
        status=issue.status,
        priority=issue.priority,
        knowledge=[
            KnowledgeView(
                id=item.id,
                type=item.type,
                summary=item.summary,
                sources=list(item.sources),
            )
            for item in knowledge
        ],
    )
