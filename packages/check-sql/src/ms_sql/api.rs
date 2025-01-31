// Copyright (C) 2023 Checkmk GmbH - License: GNU General Public License v2
// This file is part of Checkmk (https://checkmk.com). It is subject to the terms and
// conditions defined in the file COPYING, which is part of this source code package.

use crate::config::CheckConfig;
use anyhow::Result;

use tiberius::{AuthMethod, Client, Config};
use tokio::net::TcpStream;
use tokio_util::compat::{Compat, TokioAsyncWriteCompatExt};

pub enum Credentials<'a> {
    SqlServer {
        user: &'a str,
        password: &'a str,
    },
    #[cfg(windows)]
    Windows {
        user: &'a str,
        password: &'a str,
    },
}

impl CheckConfig {
    pub async fn exec(&self) -> Result<()> {
        Ok(())
    }
}

/// Check SQL connection to MS SQL
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server
/// * `credentials` - defines connection type and credentials itself
pub async fn create_client(
    host: &str,
    port: u16,
    credentials: Credentials<'_>,
) -> Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host(host);
    config.port(port);
    config.authentication(match credentials {
        Credentials::SqlServer { user, password } => AuthMethod::sql_server(user, password),
        #[cfg(windows)]
        Credentials::Windows { user, password } => AuthMethod::windows(user, password),
    });
    config.trust_cert(); // on production, it is not a good idea to do this

    let tcp = TcpStream::connect(config.get_addr()).await?;
    tcp.set_nodelay(true)?;

    // To be able to use Tokio's tcp, we're using the `compat_write` from
    // the `TokioAsyncWriteCompatExt` to get a stream compatible with the
    // traits from the `futures` crate.
    Ok(Client::connect(config, tcp.compat_write()).await?)
}

/// Check Integrated connection to MS SQL
///
/// # Arguments
///
/// * `host` - Hostname of MS SQL server
/// * `port` - Port of MS SQL server
#[cfg(windows)]
pub async fn create_client_for_logged_user(
    host: &str,
    port: u16,
) -> Result<Client<Compat<TcpStream>>> {
    let mut config = Config::new();

    config.host(host);
    config.port(port);
    config.authentication(AuthMethod::Integrated);
    config.trust_cert(); // on production, it is not a good idea to do this

    let tcp = TcpStream::connect(config.get_addr()).await?;
    tcp.set_nodelay(true)?;

    // To be able to use Tokio's tcp, we're using the `compat_write` from
    // the `TokioAsyncWriteCompatExt` to get a stream compatible with the
    // traits from the `futures` crate.
    Ok(Client::connect(config, tcp.compat_write()).await?)
}

#[cfg(unix)]
pub async fn create_client_for_logged_user(
    _host: &str,
    _port: u16,
) -> Result<Client<Compat<TcpStream>>> {
    anyhow::bail!("not supported");
}
