from __future__ import annotations

import logging
from pathlib import Path
from typing import Any

import fastf1
import pandas as pd

from app.core.config import get_settings
from app.schemas.session import DriverInfo, DriverResult, Lap, PitStop, SessionData, Stint

logger = logging.getLogger(__name__)

_cache_configured = False


class SessionNotFoundError(Exception):
    """Raised when a year/round/session_type cannot be loaded from FastF1."""


def configure_fastf1_cache() -> None:
    """Enable the FastF1 on-disk cache. Safe to call multiple times."""
    global _cache_configured
    if _cache_configured:
        return

    cache_dir = Path(get_settings().fastf1_cache_dir)
    cache_dir.mkdir(parents=True, exist_ok=True)
    fastf1.Cache.enable_cache(str(cache_dir))
    _cache_configured = True


def load_session_data(year: int, round: int, session_type: str = "R") -> SessionData:
    """Load and normalize a FastF1 session into plain Pydantic models.

    Raises:
        SessionNotFoundError: if the year/round/session_type does not exist
            or FastF1 fails to load it at all.
    """
    configure_fastf1_cache()

    try:
        session = fastf1.get_session(year, round, session_type)
        session.load(laps=True, telemetry=False, weather=False, messages=False)
    except Exception as exc:
        raise SessionNotFoundError(
            f"Could not load session year={year} round={round} "
            f"session_type={session_type!r}: {exc}"
        ) from exc

    event_name = _event_name(session)
    country = _country(session)
    total_laps = _total_laps(session)
    laps_df = session.laps

    if laps_df is None or laps_df.empty:
        logger.warning(
            "No lap data available for year=%s round=%s session_type=%s",
            year, round, session_type,
        )
        return SessionData(
            year=year,
            round=round,
            session_type=session_type,
            event_name=event_name,
            country=country,
            total_laps=total_laps,
            laps=[],
            pit_stops=[],
            stints=[],
            drivers=[],
            results=[],
            data_complete=False,
        )

    # Each check below is independent: data_complete becomes False as soon as
    # ANY one category (pit stops, tyre compounds, sector times) is entirely
    # missing, even if the other categories are fully present. E.g. a session
    # with full lap/compound/sector data but zero recorded pit stops still
    # yields data_complete=False, since pit stop timing matters for strategy
    # comparison even when derivable data (stints) is otherwise complete.
    data_complete = True

    if laps_df["PitInTime"].isna().all():
        logger.warning("No pit stop data available for year=%s round=%s", year, round)
        data_complete = False

    if laps_df["Compound"].isna().all():
        logger.warning("No tyre compound data available for year=%s round=%s", year, round)
        data_complete = False

    sector_columns = ["Sector1Time", "Sector2Time", "Sector3Time"]
    if laps_df[sector_columns].isna().all().all():
        logger.warning("No sector time data available for year=%s round=%s", year, round)
        data_complete = False

    driver_codes = _unique_driver_codes(laps_df)

    return SessionData(
        year=year,
        round=round,
        session_type=session_type,
        event_name=event_name,
        country=country,
        total_laps=total_laps,
        laps=_build_laps(laps_df),
        pit_stops=_build_pit_stops(laps_df),
        stints=_build_stints(laps_df),
        drivers=_build_drivers(session, driver_codes),
        results=_build_results(session, driver_codes),
        data_complete=data_complete,
    )


def _event_name(session: Any) -> str | None:
    try:
        return str(session.event["EventName"])
    except Exception:
        return None


def _country(session: Any) -> str | None:
    try:
        value = session.event["Country"]
        return str(value) if isinstance(value, str) and value else None
    except Exception:
        return None


def _total_laps(session: Any) -> int | None:
    try:
        return _to_int(session.total_laps)
    except Exception:
        return None


def _to_seconds(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return value.total_seconds()


def _to_int(value: Any) -> int | None:
    if value is None or pd.isna(value):
        return None
    return int(value)


def _to_float(value: Any) -> float | None:
    if value is None or pd.isna(value):
        return None
    return float(value)


def _build_laps(laps_df: pd.DataFrame) -> list[Lap]:
    laps: list[Lap] = []
    for row in laps_df.itertuples():
        laps.append(
            Lap(
                driver=row.Driver,
                lap_number=_to_int(row.LapNumber) or 0,
                lap_time_seconds=_to_seconds(row.LapTime),
                sector_1_seconds=_to_seconds(row.Sector1Time),
                sector_2_seconds=_to_seconds(row.Sector2Time),
                sector_3_seconds=_to_seconds(row.Sector3Time),
                compound=row.Compound if isinstance(row.Compound, str) else None,
                tyre_life=_to_int(row.TyreLife),
                position=_to_int(row.Position),
                track_status=row.TrackStatus if isinstance(row.TrackStatus, str) else None,
            )
        )
    return laps


def _build_pit_stops(laps_df: pd.DataFrame) -> list[PitStop]:
    """A pit stop is a lap with PitInTime set; duration is derived from the
    following lap's PitOutTime (pit entry to pit exit)."""
    pit_stops: list[PitStop] = []

    for driver, driver_laps in laps_df.groupby("Driver"):
        driver_laps = driver_laps.sort_values("LapNumber")
        pit_in_laps = driver_laps[driver_laps["PitInTime"].notna()]

        for _, row in pit_in_laps.iterrows():
            duration = None
            later_laps = driver_laps[driver_laps["LapNumber"] > row["LapNumber"]]
            if not later_laps.empty:
                next_row = later_laps.iloc[0]
                if pd.notna(next_row["PitOutTime"]):
                    duration = _to_seconds(next_row["PitOutTime"] - row["PitInTime"])

            pit_stops.append(
                PitStop(
                    driver=str(driver),
                    lap_number=_to_int(row["LapNumber"]) or 0,
                    duration_seconds=duration,
                )
            )

    return pit_stops


def _build_stints(laps_df: pd.DataFrame) -> list[Stint]:
    stints: list[Stint] = []

    # groupby() drops NaN group keys by default, so rows without a Stint
    # number (e.g. an incomplete lap) are already excluded from the groups
    # below without needing an explicit check.
    for (driver, stint_number), stint_laps in laps_df.groupby(["Driver", "Stint"]):
        compounds = stint_laps["Compound"].dropna().unique()
        compound = str(compounds[0]) if len(compounds) > 0 else None

        stints.append(
            Stint(
                driver=str(driver),
                stint_number=_to_int(stint_number) or 0,
                compound=compound,
                start_lap=_to_int(stint_laps["LapNumber"].min()) or 0,
                end_lap=_to_int(stint_laps["LapNumber"].max()) or 0,
            )
        )

    return stints


def _unique_driver_codes(laps_df: pd.DataFrame) -> list[str]:
    """Driver codes in their first-appearance order in the laps data —
    the canonical driver ordering shared by _build_drivers and
    _build_results, so both line up with the same session.results rows."""
    codes: list[str] = []
    seen: set[str] = set()
    for code in laps_df["Driver"]:
        if code not in seen:
            seen.add(code)
            codes.append(code)
    return codes


def _build_drivers(session: Any, driver_codes: list[str]) -> list[DriverInfo]:
    """One DriverInfo per driver who has laps in this session. Name/
    number/team come from session.results (a separate FastF1 dataset,
    keyed by driver code) when available; a driver missing from results
    (or a session with no usable results at all — e.g. very old/
    incomplete data) still gets an entry, just with those fields as None
    rather than dropping the driver or raising.
    """
    info_by_code: dict[str, DriverInfo] = {}
    try:
        results = session.results
        if results is not None and not results.empty:
            for row in results.itertuples():
                code = getattr(row, "Abbreviation", None)
                if not isinstance(code, str) or not code:
                    continue
                full_name = getattr(row, "FullName", None)
                team_name = getattr(row, "TeamName", None)
                info_by_code[code] = DriverInfo(
                    code=code,
                    full_name=full_name if isinstance(full_name, str) and full_name else None,
                    number=_to_int(getattr(row, "DriverNumber", None)),
                    team_name=team_name if isinstance(team_name, str) and team_name else None,
                )
    except Exception:
        logger.warning("Could not read session.results for driver info", exc_info=True)

    return [info_by_code.get(code, DriverInfo(code=code)) for code in driver_codes]


def _build_results(session: Any, driver_codes: list[str]) -> list[DriverResult]:
    """One DriverResult per driver (final classification) — see
    DriverResult's docstring for the total_time_seconds vs.
    gap_to_leader_seconds split. Degrades the same way _build_drivers
    does: missing/unreadable session.results never raises, drivers just
    fall back to a bare DriverResult(code=code).
    """
    result_by_code: dict[str, DriverResult] = {}
    try:
        results = session.results
        if results is not None and not results.empty:
            for row in results.itertuples():
                code = getattr(row, "Abbreviation", None)
                if not isinstance(code, str) or not code:
                    continue

                position = _to_int(getattr(row, "Position", None))
                classified_position_raw = getattr(row, "ClassifiedPosition", None)
                status_raw = getattr(row, "Status", None)
                time_value = getattr(row, "Time", None)

                total_time_seconds = _to_seconds(time_value) if position == 1 else None
                gap_to_leader_seconds = _to_seconds(time_value) if position != 1 else None

                result_by_code[code] = DriverResult(
                    code=code,
                    position=position,
                    classified_position=(
                        str(classified_position_raw)
                        if isinstance(classified_position_raw, str) and classified_position_raw
                        else None
                    ),
                    status=str(status_raw) if isinstance(status_raw, str) and status_raw else None,
                    total_time_seconds=total_time_seconds,
                    gap_to_leader_seconds=gap_to_leader_seconds,
                    points=_to_float(getattr(row, "Points", None)),
                )
    except Exception:
        logger.warning("Could not read session.results for classification", exc_info=True)

    return [result_by_code.get(code, DriverResult(code=code)) for code in driver_codes]
