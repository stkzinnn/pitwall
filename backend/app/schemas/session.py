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


class DriverResult(BaseModel):
    """Final classification for one driver, from FastF1's session.results
    — see fastf1_client._build_results. Fields beyond `code` degrade to
    None when results aren't available (graceful degradation, same policy
    as DriverInfo).

    Pit-stop count and real tyre strategy are deliberately NOT duplicated
    here: SessionData.pit_stops / SessionData.stints already carry that,
    per driver (via the `driver` field), for the whole session — a
    consumer filters those by this driver's `code` instead of the backend
    repeating the same rows in two places.
    """

    code: str
    position: int | None = None
    # FastF1's own classification code: a plain rank ("1", "2", ...) or a
    # symbol like "R" (retired) / "NC" (not classified) — kept as a string
    # since it isn't always numeric.
    classified_position: str | None = None
    status: str | None = None
    # Race winner only (everyone else's absolute time isn't meaningful
    # without also knowing the winner's — see gap_to_leader_seconds).
    total_time_seconds: float | None = None
    # Everyone except the winner: gap to the winner, matching how FastF1
    # (and official F1 timing) reports it.
    gap_to_leader_seconds: float | None = None
    points: float | None = None


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
    results: list[DriverResult] = []
    data_complete: bool = True
