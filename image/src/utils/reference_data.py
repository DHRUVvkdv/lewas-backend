"""
Reference data utilities for the LEWAS sensor API.
"""

import json
import os
import logging
from typing import Dict, Optional, Any, List

# Configure logging
logger = logging.getLogger(__name__)

# Cache for reference data
_instruments_cache = None
_units_cache = None
_metrics_cache = None
_meta_cells_cache = None

# Path to reference data files
REFERENCE_DATA_PATH = os.path.join(
    os.path.dirname(os.path.dirname(__file__)), "reference_data"
)


def _load_json_file(filename: str) -> Dict:
    """Load a JSON file and return its contents as a dictionary."""
    try:
        file_path = os.path.join(REFERENCE_DATA_PATH, filename)
        with open(file_path, "r") as f:
            return json.load(f)
    except Exception as e:
        logger.error(f"Error loading reference data file {filename}: {e}")
        return {}


def get_instruments() -> Dict[str, Dict[str, Any]]:
    """Get the instruments reference data."""
    global _instruments_cache
    if _instruments_cache is None:
        data = _load_json_file("instruments.json")
        _instruments_cache = {
            item["name"]: item for item in data.get("instruments", [])
        }
    return _instruments_cache


def get_units() -> Dict[str, Dict[str, Any]]:
    """Get the units reference data."""
    global _units_cache
    if _units_cache is None:
        data = _load_json_file("units.json")
        _units_cache = {item["abbv"]: item for item in data.get("units", [])}
    return _units_cache


def get_metrics() -> Dict[str, Dict[str, Any]]:
    """Get the metrics reference data."""
    global _metrics_cache
    if _metrics_cache is None:
        data = _load_json_file("metrics.json")
        # Create a lookup by name+medium combination
        _metrics_cache = {}
        for item in data.get("metrics", []):
            key = f"{item['name']}:{item['medium']}"
            _metrics_cache[key] = item
    return _metrics_cache


def get_meta_cells() -> Dict[str, Dict[str, Any]]:
    """Get the meta cells reference data."""
    global _meta_cells_cache
    if _meta_cells_cache is None:
        data = _load_json_file("meta_cells.json")
        _meta_cells_cache = {item["name"]: item for item in data.get("meta_cells", [])}
    return _meta_cells_cache


def get_instrument_id(instrument_name: str) -> Optional[int]:
    """Get the instrument ID for an instrument name."""
    instruments = get_instruments()
    instrument = instruments.get(instrument_name)
    if instrument:
        return instrument["instrument_id"]
    return None


def get_unit_id(unit_abbv: str) -> Optional[int]:
    """Get the unit ID for a unit abbreviation."""
    units = get_units()
    unit = units.get(unit_abbv)
    if unit:
        return unit["unit_id"]
    return None


def get_metric_id(metric_name: str, medium: str) -> Optional[int]:
    """Get the metric ID for a metric name and medium."""
    metrics = get_metrics()
    key = f"{metric_name}:{medium}"
    metric = metrics.get(key)
    if metric:
        return metric["metric_id"]
    return None


def get_meta_id(meta_name: str) -> Optional[int]:
    """Get the meta ID for a meta name."""
    meta_cells = get_meta_cells()
    meta_cell = meta_cells.get(meta_name)
    if meta_cell:
        return meta_cell["meta_id"]
    return None


def get_all_metrics() -> List[Dict[str, Any]]:
    """Get all metrics."""
    data = _load_json_file("metrics.json")
    return data.get("metrics", [])


def get_all_instruments() -> List[Dict[str, Any]]:
    """Get all instruments."""
    data = _load_json_file("instruments.json")
    return data.get("instruments", [])


def get_all_units() -> List[Dict[str, Any]]:
    """Get all units."""
    data = _load_json_file("units.json")
    return data.get("units", [])
