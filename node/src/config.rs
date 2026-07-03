use std::env;

#[derive(Clone, Debug)]
pub struct NodeConfig {
    pub server_url: String,
    pub node_id: String,
    pub node_token: String,
    pub private_key_path: String,
}

impl NodeConfig {
    /// Build configuration from environment variables.
    ///
    /// Required:
    ///   TANDEM_SERVER_URL — base URL of the Tandem server (e.g. "http://localhost:8080")
    ///
    /// Optional:
    ///   TANDEM_NODE_ID         — set after registration
    ///   TANDEM_NODE_TOKEN      — set after registration
    ///   TANDEM_PRIVATE_KEY_PATH — path to RSA private key PEM (default: "./node_key.pem")
    pub fn from_env() -> Self {
        let server_url = env::var("TANDEM_SERVER_URL")
            .expect("TANDEM_SERVER_URL must be set in the environment or .env file");

        let node_id = env::var("TANDEM_NODE_ID").unwrap_or_default();
        let node_token = env::var("TANDEM_NODE_TOKEN").unwrap_or_default();
        let private_key_path =
            env::var("TANDEM_PRIVATE_KEY_PATH").unwrap_or_else(|_| "./node_key.pem".to_string());

        Self {
            server_url,
            node_id,
            node_token,
            private_key_path,
        }
    }
}
