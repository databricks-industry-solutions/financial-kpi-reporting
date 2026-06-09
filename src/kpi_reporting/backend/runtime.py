from .config import AppConfig
from .logger import logger


class Runtime:
    def __init__(self, config: AppConfig) -> None:
        self.config = config
        self._lakebase = None
        self._confluence = None
        self._genie = None

    @property
    def lakebase(self):
        if self._lakebase is None:
            if self.config.force_mock:
                logger.info("force_mock enabled, using mock data")
                from .mock_data import MockLakebaseClient
                self._lakebase = MockLakebaseClient()
            else:
                try:
                    from .lakebase import LakebaseClient
                    client = LakebaseClient(
                        self.config.lakebase_project,
                        pg_host=self.config.pg_host,
                        pg_user=self.config.pg_user,
                        pg_password=self.config.pg_password,
                        pg_endpoint_name=self.config.pg_endpoint_name,
                    )
                    # Test connection by running a simple query
                    client.get_departments()
                    self._lakebase = client
                    logger.info(f"Lakebase client initialized (project={self.config.lakebase_project})")
                except Exception as e:
                    logger.warning(f"Lakebase unavailable ({e}), using mock data")
                    from .mock_data import MockLakebaseClient
                    self._lakebase = MockLakebaseClient()
        return self._lakebase

    @property
    def genie(self):
        if self._genie is None:
            from .genie import GenieClient
            self._genie = GenieClient(self.config.genie_space_id)
            logger.info(f"Genie client initialized (space={self.config.genie_space_id})")
        return self._genie

    @property
    def confluence(self):
        if self._confluence is None:
            from .confluence import ConfluenceClient
            self._confluence = ConfluenceClient(
                base_url=self.config.confluence_base_url,
                api_token=self.config.confluence_api_token,
                user_email=self.config.confluence_user_email,
                space_key=self.config.confluence_space_key,
                parent_page_id=self.config.confluence_parent_page_id,
            )
            logger.info("Confluence client initialized")
        return self._confluence
