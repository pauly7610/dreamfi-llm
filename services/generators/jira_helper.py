import logging
from typing import Dict, Any, Optional, List
from integrations.jira_client import JiraClient

log = logging.getLogger(__name__)


class JiraHelper:
    def __init__(self):
        self.client = JiraClient()

    def fetch_epic_data(self, epic_key: str) -> Dict[str, Any]:
        try:
            issue = self.client._jira.issue(epic_key)
            stories = self.client.get_epic_stories(epic_key)

            return {
                "epic_key": epic_key,
                "summary": issue.get("fields", {}).get("summary", ""),
                "description": issue.get("fields", {}).get("description", ""),
                "status": issue.get("fields", {}).get("status", {}).get("name", ""),
                "assignee": issue.get("fields", {}).get("assignee", {}).get("displayName", "Unassigned"),
                "created": issue.get("fields", {}).get("created", ""),
                "updated": issue.get("fields", {}).get("updated", ""),
                "story_count": len(stories),
                "stories": [
                    {
                        "key": s.get("key"),
                        "summary": s.get("fields", {}).get("summary", ""),
                        "status": s.get("fields", {}).get("status", {}).get("name", ""),
                    }
                    for s in stories[:10]
                ],
            }
        except Exception as e:
            log.error(f"Failed to fetch epic {epic_key}: {e}")
            return {}

    def format_as_jira_story(self, story_data: Dict[str, Any]) -> str:
        title = story_data.get("title", "User Story")
        description = story_data.get("description", "")
        acceptance_criteria = story_data.get("acceptance_criteria", [])

        story = f"## {title}\n\n"
        story += f"{description}\n\n"
        story += "### Acceptance Criteria\n"
        for criterion in acceptance_criteria:
            story += f"- [ ] {criterion}\n"

        return story

    def get_story_template(self) -> str:
        return """## User Story Template

**As a** [user role]
**I want** [capability]
**So that** [business value]

### Description
[Detailed description of the feature]

### Acceptance Criteria
- [ ] Criterion 1
- [ ] Criterion 2
- [ ] Criterion 3

### Technical Details
- Estimated points: ?
- Dependencies: None
- Labels: ?

### Notes
[Any additional context]
"""

    def create_stories_from_template(
        self,
        epic_key: str,
        stories_data: List[Dict[str, Any]],
        project_key: str
    ) -> List[Dict[str, Any]]:
        results = []
        for story_data in stories_data:
            try:
                description = self.format_as_jira_story(story_data)

                issue_dict = {
                    "project": {"key": project_key},
                    "summary": story_data.get("title", "Story"),
                    "description": description,
                    "issuetype": {"name": "Story"},
                    "parent": {"key": epic_key},
                }

                if "assignee" in story_data:
                    issue_dict["assignee"] = {"name": story_data["assignee"]}

                created = self.client._jira.create_issue(fields=issue_dict)

                results.append({
                    "success": True,
                    "key": created.get("key"),
                    "id": created.get("id"),
                })
            except Exception as e:
                log.error(f"Failed to create story: {e}")
                results.append({
                    "success": False,
                    "error": str(e),
                })

        return results

    def link_to_epic(self, story_key: str, epic_key: str) -> bool:
        try:
            self.client._jira.create_issue_link(
                type="Epic",
                inwardIssue=epic_key,
                outwardIssue=story_key
            )
            log.info(f"Linked {story_key} to epic {epic_key}")
            return True
        except Exception as e:
            log.error(f"Failed to link to epic: {e}")
            return False
