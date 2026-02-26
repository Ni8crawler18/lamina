"""OFAC SDN (Specially Designated Nationals) screener.

Downloads the real OFAC SDN list from treasury.gov, parses names and crypto
addresses, and provides fuzzy name matching + exact address matching.
"""

import csv
import io
import logging
import os
from datetime import datetime, timezone

import aiohttp
from rapidfuzz import fuzz

logger = logging.getLogger(__name__)

SDN_URL = "https://www.treasury.gov/ofac/downloads/sdn.csv"
ADD_URL = "https://www.treasury.gov/ofac/downloads/add.csv"

DATA_DIR = os.path.join(os.path.dirname(__file__), "..", "data")
SDN_CACHE = os.path.join(DATA_DIR, "sdn_cache.csv")
ADD_CACHE = os.path.join(DATA_DIR, "add_cache.csv")

MATCH_THRESHOLD = 85  # Jaro-Winkler-weighted ratio threshold


class OFACScreener:
    """Singleton screener that holds the parsed SDN list in memory."""

    _instance = None

    def __init__(self):
        self.names: list[tuple[int, str]] = []          # (entry_id, name)
        self.alt_names: list[tuple[int, str]] = []      # (entry_id, alt_name)
        self.addresses: dict[str, int] = {}              # address -> entry_id
        self.entry_details: dict[int, dict] = {}         # entry_id -> metadata
        self.loaded = False
        self.loaded_at: str | None = None

    @classmethod
    def get_instance(cls) -> "OFACScreener":
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance

    async def load(self) -> None:
        """Download SDN + address CSVs (or load from cache) and parse into memory."""
        os.makedirs(DATA_DIR, exist_ok=True)

        sdn_text = await self._fetch_or_cache(SDN_URL, SDN_CACHE)
        add_text = await self._fetch_or_cache(ADD_URL, ADD_CACHE)

        if sdn_text is None:
            logger.warning("OFAC screener: no SDN data available — screening disabled")
            return

        self._parse_sdn(sdn_text)
        if add_text:
            self._parse_addresses(add_text)

        self.loaded = True
        self.loaded_at = datetime.now(timezone.utc).isoformat()
        logger.info(
            f"OFAC screener loaded: {len(self.names)} entries, "
            f"{len(self.addresses)} addresses"
        )

    async def _fetch_or_cache(self, url: str, cache_path: str) -> str | None:
        """Try to download from URL; fall back to local cache."""
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(url, timeout=aiohttp.ClientTimeout(total=30)) as resp:
                    if resp.status == 200:
                        text = await resp.text(encoding="latin-1")
                        with open(cache_path, "w", encoding="utf-8") as f:
                            f.write(text)
                        logger.info(f"Downloaded {url} → {cache_path}")
                        return text
                    logger.warning(f"OFAC download {url} returned status {resp.status}")
        except Exception as e:
            logger.warning(f"OFAC download failed ({url}): {e}")

        # Fall back to cache
        if os.path.exists(cache_path):
            logger.info(f"Using cached OFAC data: {cache_path}")
            with open(cache_path, "r", encoding="utf-8") as f:
                return f.read()

        return None

    def _parse_sdn(self, text: str) -> None:
        """Parse the SDN CSV. Columns: ent_num, SDN_Name, SDN_Type, Program, Title, ..."""
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            if len(row) < 2:
                continue
            try:
                entry_id = int(row[0])
            except (ValueError, IndexError):
                continue

            name = row[1].strip()
            if not name or name == "-0-":
                continue

            sdn_type = row[2].strip() if len(row) > 2 else ""
            program = row[3].strip() if len(row) > 3 else ""

            self.names.append((entry_id, name.upper()))
            self.entry_details[entry_id] = {
                "entry_id": entry_id,
                "name": name,
                "sdn_type": sdn_type,
                "program": program,
            }

    def _parse_addresses(self, text: str) -> None:
        """Parse the ADD CSV for crypto addresses. Columns: ent_num, add_num, address, ..., remarks."""
        reader = csv.reader(io.StringIO(text))
        for row in reader:
            if len(row) < 6:
                continue
            try:
                entry_id = int(row[0])
            except (ValueError, IndexError):
                continue

            # Crypto addresses are in the "remarks" column and contain "Digital Currency Address"
            # Also check the address field itself
            remarks = row[-1].strip() if row else ""
            if "Digital Currency Address" in remarks:
                # Extract addresses from remarks like "Digital Currency Address - XBT abc123def;"
                parts = remarks.split(";")
                for part in parts:
                    part = part.strip()
                    if "Digital Currency Address" in part:
                        # Format: "Digital Currency Address - XBT abc123..."
                        addr_parts = part.split(" - ", 1)
                        if len(addr_parts) > 1:
                            # May be "XBT abc123" or just the address
                            tokens = addr_parts[1].strip().split()
                            if len(tokens) >= 2:
                                addr = tokens[-1].rstrip(";").strip()
                            else:
                                addr = tokens[0].rstrip(";").strip()
                            if addr:
                                self.addresses[addr.upper()] = entry_id

    def screen_name(self, name: str) -> dict:
        """Fuzzy-match a name against the SDN list. Returns screening result."""
        if not self.loaded or not name:
            return {"is_match": False, "score": 0, "details": None}

        name_upper = name.upper()
        best_score = 0
        best_entry_id = None

        for entry_id, sdn_name in self.names:
            score = fuzz.WRatio(name_upper, sdn_name)
            if score > best_score:
                best_score = score
                best_entry_id = entry_id
                if score == 100:
                    break

        if best_score >= MATCH_THRESHOLD and best_entry_id is not None:
            return {
                "is_match": True,
                "score": best_score,
                "match_type": "name_fuzzy",
                "details": self.entry_details.get(best_entry_id),
            }

        return {"is_match": False, "score": best_score, "details": None}

    def screen_address(self, address: str) -> dict:
        """Exact-match an address against known sanctioned crypto addresses."""
        if not self.loaded or not address:
            return {"is_match": False, "score": 0, "details": None}

        addr_upper = address.upper()
        entry_id = self.addresses.get(addr_upper)
        if entry_id is not None:
            return {
                "is_match": True,
                "score": 100,
                "match_type": "address_exact",
                "details": self.entry_details.get(entry_id),
            }

        return {"is_match": False, "score": 0, "details": None}

    def screen(self, name: str | None = None, address: str | None = None) -> dict:
        """Combined screening — returns worst-case (match if either hits)."""
        name_result = self.screen_name(name) if name else {"is_match": False, "score": 0, "details": None}
        addr_result = self.screen_address(address) if address else {"is_match": False, "score": 0, "details": None}

        if addr_result["is_match"]:
            return addr_result
        if name_result["is_match"]:
            return name_result

        return {
            "is_match": False,
            "score": max(name_result.get("score", 0), addr_result.get("score", 0)),
            "details": None,
        }

    def get_status(self) -> dict:
        return {
            "loaded": self.loaded,
            "entry_count": len(self.names),
            "address_count": len(self.addresses),
            "loaded_at": self.loaded_at,
        }
