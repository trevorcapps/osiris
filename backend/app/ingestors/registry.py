from app.ingestors.gdelt import GDELTIngestor
from app.ingestors.usgs import USGSIngestor
from app.ingestors.opensky import OpenSkyIngestor
from app.ingestors.nasa_eonet import NASAEONETIngestor
from app.ingestors.noaa import NOAAIngestor
from app.ingestors.nasa_firms import NASAFIRMSIngestor
from app.ingestors.acled import ACLEDIngestor
from app.ingestors.reliefweb import ReliefWebIngestor
from app.ingestors.cisa_kev import CISAKEVIngestor
from app.ingestors.ofac import OFACIngestor
from app.ingestors.opensanctions import OpenSanctionsIngestor
from app.ingestors.greynoise import GreyNoiseIngestor
from app.ingestors.otx import OTXIngestor
from app.ingestors.shodan_feed import ShodanIngestor
from app.ingestors.rss_news import RSSNewsIngestor
from app.ingestors.x_osint import XOSINTIngestor
from app.ingestors.reddit import RedditIngestor
from app.ingestors.who import WHOIngestor
from app.ingestors.submarine_cables import SubmarineCableIngestor
from app.ingestors.volcano import VolcanoIngestor
from app.ingestors.unhcr import UNHCRIngestor
from app.ingestors.ioda import IODAIngestor

ALL_INGESTORS = [
    GDELTIngestor(),
    USGSIngestor(),
    OpenSkyIngestor(),
    NASAEONETIngestor(),
    NOAAIngestor(),
    NASAFIRMSIngestor(),
    ACLEDIngestor(),
    ReliefWebIngestor(),
    CISAKEVIngestor(),
    OFACIngestor(),
    OpenSanctionsIngestor(),
    GreyNoiseIngestor(),
    OTXIngestor(),
    ShodanIngestor(),
    RSSNewsIngestor(),
    XOSINTIngestor(),
    RedditIngestor(),
    WHOIngestor(),
    SubmarineCableIngestor(),
    VolcanoIngestor(),
    UNHCRIngestor(),
    IODAIngestor(),
]
