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


class SessionData(BaseModel):
    year: int
    round: int
    session_type: str
    event_name: str | None = None
    laps: list[Lap] = []
    pit_stops: list[PitStop] = []
    stints: list[Stint] = []
    data_complete: bool = True
