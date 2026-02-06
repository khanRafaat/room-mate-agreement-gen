"""
Roommate Agreement Generator - Locations Router
API endpoints for country, state, city cascading dropdowns.
"""
from fastapi import APIRouter, Depends, HTTPException, status
from sqlalchemy.orm import Session
from typing import List

from app.database import get_db
from app.models.models import Country, State, City
from app.schemas.locations import CountryResponse, StateResponse, CityResponse

router = APIRouter(prefix="/locations", tags=["locations"])


@router.get("/countries", response_model=List[CountryResponse])
async def list_countries(
    db: Session = Depends(get_db)
):
    """
    Get all active countries for dropdown.
    
    Returns countries sorted alphabetically by name.
    """
    countries = db.query(Country).filter(
        Country.is_active == True
    ).order_by(Country.name).all()
    
    return countries


@router.get("/countries/{country_id}", response_model=CountryResponse)
async def get_country(
    country_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific country by ID.
    """
    country = db.query(Country).filter(Country.id == country_id).first()
    
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )
    
    return country


@router.get("/countries/{country_id}/states", response_model=List[StateResponse])
async def list_states_by_country(
    country_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all active states/provinces for a country.
    
    Used for cascading dropdown: Country → State
    """
    # Verify country exists
    country = db.query(Country).filter(Country.id == country_id).first()
    if not country:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Country not found"
        )
    
    states = db.query(State).filter(
        State.country_id == country_id,
        State.is_active == True
    ).order_by(State.name).all()
    
    return states


@router.get("/states/{state_id}", response_model=StateResponse)
async def get_state(
    state_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific state by ID.
    """
    state = db.query(State).filter(State.id == state_id).first()
    
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State not found"
        )
    
    return state


@router.get("/states/{state_id}/cities", response_model=List[CityResponse])
async def list_cities_by_state(
    state_id: str,
    db: Session = Depends(get_db)
):
    """
    Get all active cities for a state.
    
    Used for cascading dropdown: State → City
    """
    # Verify state exists
    state = db.query(State).filter(State.id == state_id).first()
    if not state:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="State not found"
        )
    
    cities = db.query(City).filter(
        City.state_id == state_id,
        City.is_active == True
    ).order_by(City.name).all()
    
    return cities


@router.get("/cities/{city_id}", response_model=CityResponse)
async def get_city(
    city_id: str,
    db: Session = Depends(get_db)
):
    """
    Get a specific city by ID.
    """
    city = db.query(City).filter(City.id == city_id).first()
    
    if not city:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="City not found"
        )
    
    return city
