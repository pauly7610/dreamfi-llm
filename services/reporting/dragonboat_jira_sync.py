import asyncio
import logging
import json
from datetime import datetime, timedelta
from typing import Any, Optional
from uuid import uuid4
import psycopg2
from psycopg2 import sql

from integrations.dragonboat_client import DragonboatClient
from integrations.jira_client import JiraClient
from config import config as _cfg

log = logging.getLogger(__name__)


class DragonboatJiraSync:
    def __init__(self, db_url: Optional[str] = None):
        self.db_url = db_url or _cfg.__dict__.get("database_url", "postgresql://dreamfi:password@localhost:5432/dreamfi_dev")
        self.dragonboat = DragonboatClient()
        self.jira = JiraClient()
        self._ensure_tables()

    def _get_conn(self):
        return psycopg2.connect(self.db_url)

    def _ensure_tables(self):
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS dragonboat_jira_mappings (
                id UUID PRIMARY KEY,
                dragonboat_initiative_id TEXT NOT NULL,
                jira_epic_key TEXT NOT NULL,
                last_synced_at TIMESTAMP,
                sync_direction TEXT,
                conflict_status TEXT,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_dead_letter (
                id UUID PRIMARY KEY,
                dragonboat_id TEXT,
                jira_key TEXT,
                error_message TEXT,
                sync_attempt_count INT DEFAULT 1,
                created_at TIMESTAMP DEFAULT NOW()
            );
            """)
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    async def sync_dragonboat_to_jira(self, initiative_id: str) -> dict[str, Any]:
        try:
            initiatives = await self.dragonboat.async_get_initiatives()
            initiative = next((i for i in initiatives if i.get("id") == initiative_id), None)
            if not initiative:
                log.error(f"Initiative {initiative_id} not found in Dragonboat")
                return {"success": False, "error": "Initiative not found"}

            mapping = self._get_mapping(initiative_id)
            jira_epic_key = mapping.get("jira_epic_key") if mapping else None

            epic_summary = initiative.get("name", "Untitled Initiative")
            epic_description = initiative.get("description", "")
            epic_description += f"\n\n**Source:** Dragonboat Initiative {initiative_id}\n**Status:** {initiative.get('status', 'Unknown')}"

            if jira_epic_key:
                self.jira.update_epic(jira_epic_key, summary=epic_summary, description=epic_description)
                log.info(f"Updated Jira epic {jira_epic_key} from Dragonboat {initiative_id}")
            else:
                jira_project = "DMON"
                epic_response = self.jira.create_epic(
                    project_key=jira_project,
                    summary=epic_summary,
                    description=epic_description,
                )
                jira_epic_key = epic_response.get("key")
                log.info(f"Created Jira epic {jira_epic_key} from Dragonboat {initiative_id}")
                self._create_mapping(initiative_id, jira_epic_key, "dboard_to_jira")

            self._update_last_sync(initiative_id, jira_epic_key, "in_sync")
            return {"success": True, "jira_epic_key": jira_epic_key, "initiative_id": initiative_id}

        except Exception as exc:
            log.error(f"Failed to sync Dragonboat {initiative_id} to Jira: {exc}")
            self._add_to_dead_letter(initiative_id, None, str(exc))
            return {"success": False, "error": str(exc)}

    async def sync_jira_to_dragonboat(self, epic_key: str) -> dict[str, Any]:
        try:
            epic = self.jira._jira.issue(epic_key)
            epic_summary = epic["fields"].get("summary", "")
            epic_description = epic["fields"].get("description", "")

            mapping = self._get_mapping_by_jira_key(epic_key)
            dragonboat_id = mapping.get("dragonboat_initiative_id") if mapping else None

            if dragonboat_id:
                update_payload = {
                    "name": epic_summary,
                    "description": epic_description,
                    "status": epic["fields"].get("status", {}).get("name", ""),
                }
                await self.dragonboat.async_update_initiative(dragonboat_id, update_payload)
                log.info(f"Updated Dragonboat {dragonboat_id} from Jira {epic_key}")
            else:
                log.warning(f"No Dragonboat mapping found for Jira epic {epic_key}")
                return {"success": False, "error": "No mapping found"}

            self._update_last_sync(dragonboat_id, epic_key, "in_sync")
            return {"success": True, "dragonboat_id": dragonboat_id, "epic_key": epic_key}

        except Exception as exc:
            log.error(f"Failed to sync Jira {epic_key} to Dragonboat: {exc}")
            self._add_to_dead_letter(None, epic_key, str(exc))
            return {"success": False, "error": str(exc)}

    async def reconcile_differences(self) -> dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT id, dragonboat_initiative_id, jira_epic_key, last_synced_at, conflict_status
            FROM dragonboat_jira_mappings
            WHERE conflict_status != 'in_sync' OR (last_synced_at < NOW() - INTERVAL '1 hour')
            """)
            mappings = cursor.fetchall()

            conflicts = []
            for mapping in mappings:
                mapping_id, dboard_id, jira_key, last_sync, conflict_status = mapping
                try:
                    initiatives = await self.dragonboat.async_get_initiatives()
                    dboard_item = next((i for i in initiatives if i.get("id") == dboard_id), None)
                    jira_issue = self.jira._jira.issue(jira_key)

                    dboard_status = dboard_item.get("status") if dboard_item else None
                    jira_status = jira_issue["fields"].get("status", {}).get("name")

                    if dboard_status != jira_status:
                        conflicts.append({
                            "mapping_id": str(mapping_id),
                            "dragonboat_id": dboard_id,
                            "jira_key": jira_key,
                            "dboard_status": dboard_status,
                            "jira_status": jira_status,
                            "last_synced": last_sync.isoformat() if last_sync else None,
                        })
                        cursor.execute("""
                        UPDATE dragonboat_jira_mappings
                        SET conflict_status = 'conflict'
                        WHERE id = %s
                        """, (mapping_id,))
                        log.warning(f"Conflict detected: {dboard_id} ({dboard_status}) vs {jira_key} ({jira_status})")

                except Exception as exc:
                    log.error(f"Error reconciling mapping {mapping_id}: {exc}")

            conn.commit()
            return {"conflicts_found": len(conflicts), "conflicts": conflicts}

        finally:
            cursor.close()
            conn.close()

    def get_sync_status(self) -> dict[str, Any]:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT
                id,
                dragonboat_initiative_id,
                jira_epic_key,
                last_synced_at,
                sync_direction,
                conflict_status,
                created_at
            FROM dragonboat_jira_mappings
            ORDER BY last_synced_at DESC
            """)
            mappings = cursor.fetchall()

            results = []
            for mapping in mappings:
                mapping_id, dboard_id, jira_key, last_sync, direction, conflict_status, created_at = mapping
                results.append({
                    "id": str(mapping_id),
                    "dragonboat_initiative_id": dboard_id,
                    "jira_epic_key": jira_key,
                    "last_synced_at": last_sync.isoformat() if last_sync else None,
                    "sync_direction": direction,
                    "conflict_status": conflict_status,
                    "created_at": created_at.isoformat() if created_at else None,
                })

            return {
                "total_mappings": len(results),
                "mappings": results,
            }

        finally:
            cursor.close()
            conn.close()

    def _create_mapping(self, initiative_id: str, jira_key: str, direction: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO dragonboat_jira_mappings
            (id, dragonboat_initiative_id, jira_epic_key, sync_direction, conflict_status, last_synced_at)
            VALUES (%s, %s, %s, %s, %s, NOW())
            """, (str(uuid4()), initiative_id, jira_key, direction, "in_sync"))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def _get_mapping(self, initiative_id: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT id, dragonboat_initiative_id, jira_epic_key, last_synced_at, conflict_status
            FROM dragonboat_jira_mappings
            WHERE dragonboat_initiative_id = %s
            LIMIT 1
            """, (initiative_id,))
            row = cursor.fetchone()
            if row:
                mapping_id, dboard_id, jira_key, last_sync, conflict_status = row
                return {
                    "id": str(mapping_id),
                    "dragonboat_initiative_id": dboard_id,
                    "jira_epic_key": jira_key,
                    "last_synced_at": last_sync.isoformat() if last_sync else None,
                    "conflict_status": conflict_status,
                }
            return None
        finally:
            cursor.close()
            conn.close()

    def _get_mapping_by_jira_key(self, jira_key: str) -> Optional[dict[str, Any]]:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            SELECT id, dragonboat_initiative_id, jira_epic_key, last_synced_at, conflict_status
            FROM dragonboat_jira_mappings
            WHERE jira_epic_key = %s
            LIMIT 1
            """, (jira_key,))
            row = cursor.fetchone()
            if row:
                mapping_id, dboard_id, jira_key_result, last_sync, conflict_status = row
                return {
                    "id": str(mapping_id),
                    "dragonboat_initiative_id": dboard_id,
                    "jira_epic_key": jira_key_result,
                    "last_synced_at": last_sync.isoformat() if last_sync else None,
                    "conflict_status": conflict_status,
                }
            return None
        finally:
            cursor.close()
            conn.close()

    def _update_last_sync(self, initiative_id: str, jira_key: str, status: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            UPDATE dragonboat_jira_mappings
            SET last_synced_at = NOW(), conflict_status = %s
            WHERE dragonboat_initiative_id = %s AND jira_epic_key = %s
            """, (status, initiative_id, jira_key))
            conn.commit()
        finally:
            cursor.close()
            conn.close()

    def _add_to_dead_letter(self, initiative_id: Optional[str], jira_key: Optional[str], error_msg: str) -> None:
        conn = self._get_conn()
        cursor = conn.cursor()
        try:
            cursor.execute("""
            INSERT INTO sync_dead_letter
            (id, dragonboat_id, jira_key, error_message, sync_attempt_count)
            VALUES (%s, %s, %s, %s, 1)
            """, (str(uuid4()), initiative_id, jira_key, error_msg))
            conn.commit()
        finally:
            cursor.close()
            conn.close()
