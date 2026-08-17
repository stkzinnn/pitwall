from pydantic import BaseModel


class Lap(BaseModel):
    driver: str
    lap_number: int
    lap_time_seconds: float | None = None
    sector_1_seconds: float | None = None
    sector_2_seconds: float | None = None
    sector_3_seconds: float | None = None
    compound: str | None = None
    tyre_life: int | None = None
    position: int | None = None
    # Raw FastF1 TrackStatus for this lap (e.g. "1", "126"), a string of one
    # digit per status change during the lap. None for older/incomplete
    # data — see fastf1_client.load_session_data, where a missing track
    # status never flips data_complete to False (graceful degradation, not
    # an error).
    track_status: str | None = None


class PitStop(BaseModel):
    driver: str
    lap_number: int
    duration_seconds: float | None = None


class Stint(BaseModel):
    driver: str
    stint_number: int
    compound: str | None = None
    start_lap: int
    end_lap: int


class DriverInfo(BaseModel):
    """Static info about a driver for this session (from FastF1's
    session.results, not per-lap data). Fields beyond `code` degrade to
    None rather than failing when a session's results are incomplete —
    see fastf1_client._build_drivers."""

    code: str
    full_name: str | None = None
    number: int | None = None
    team_name: str | None = None


class SessionData(BaseModel):
    year: int
    round: int
    session_type: str
    event_name: str | None = None
    country: str | None = None
    total_laps: int | None = None
    laps: list[Lap] = []
    pit_stops: list[PitStop] = []
    stints: list[Stint] = []
    drivers: list[DriverInfo] = []
    data_complete: bool = True
