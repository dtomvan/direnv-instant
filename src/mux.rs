use std::{env, io, process::Command};

use crate::daemon::DaemonContext;

const PANE_HEIGHT: &str = "10";

#[non_exhaustive]
#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Multiplexer {
    Tmux,
    Zellij,
}

impl Multiplexer {
    pub fn detect() -> Option<Self> {
        if env::var("TMUX").is_ok() {
            return Some(Self::Tmux);
        }

        if env::var("ZELLIJ").is_ok() {
            return Some(Self::Zellij);
        }

        None
    }

    pub fn spawn(&self, ctx: &DaemonContext) -> io::Result<()> {
        // Use full path to binary so the multiplexer can find it
        let bin = env::current_exe()
            .ok()
            .and_then(|p| p.to_str().map(String::from))
            .unwrap_or_else(|| "direnv-instant".to_string());

        let mux_bin = match self {
            Multiplexer::Tmux => "tmux",
            Multiplexer::Zellij => "zellij",
        };

        let mux_args = match self {
            Multiplexer::Tmux => vec!["split-window", "-d", "-l", PANE_HEIGHT],
            Multiplexer::Zellij => vec![
                "action",
                "new-pane",
                "-d",
                "down",
                "--width",
                PANE_HEIGHT,
                "--",
            ],
        };

        Command::new(mux_bin)
            .args(mux_args)
            .args([
                &bin,
                "watch",
                &ctx.temp_stderr.to_string_lossy(),
                &ctx.socket_path.to_string_lossy(),
            ])
            .spawn()
            .map(|_| ())
    }

    pub fn mux_delay_ms(&self) -> u64 {
        let specific_env = match self {
            Multiplexer::Tmux => "DIRENV_INSTANT_TMUX_DELAY",
            Multiplexer::Zellij => "DIRENV_INSTANT_ZELLIJ_DELAY",
        };

        ([specific_env, "DIRENV_INSTANT_MUX_DELAY"])
            .iter()
            .map(env::var)
            .flat_map(Result::ok)
            .next()
            .and_then(|s| s.parse::<u64>().ok())
            .map(|s| s * 1000)
            .unwrap_or(4000)
    }
}
