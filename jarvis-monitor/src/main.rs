// src/main.rs — jarvis-monitor Ratatui TUI Dashboard
// Reads from events.db and metrics.db (no live HTTP polling).
// Two-task tokio runtime: data poller (500ms) + render loop.

mod app;
mod data;
mod ui;

use std::io;
use std::time::Duration;
use crossterm::{
    event::{self, DisableMouseCapture, EnableMouseCapture, Event, KeyCode},
    execute,
    terminal::{disable_raw_mode, enable_raw_mode, EnterAlternateScreen, LeaveAlternateScreen},
};
use ratatui::{backend::CrosstermBackend, Terminal};
use tokio::sync::mpsc;

use app::{App, AppUpdate};
use data::poll_data;

#[tokio::main]
async fn main() -> anyhow::Result<()> {
    // Terminal setup
    enable_raw_mode()?;
    let mut stdout = io::stdout();
    execute!(stdout, EnterAlternateScreen, EnableMouseCapture)?;
    let backend = CrosstermBackend::new(stdout);
    let mut terminal = Terminal::new(backend)?;

    let mut app = App::new();
    let (tx, mut rx) = mpsc::channel::<AppUpdate>(32);

    // Data poller task
    let tx_clone = tx.clone();
    tokio::spawn(async move {
        loop {
            if let Some(update) = poll_data().await {
                let _ = tx_clone.send(update).await;
            }
            tokio::time::sleep(Duration::from_millis(500)).await;
        }
    });

    // Main loop with cleanup guard
    let result = run_app(&mut terminal, &mut app, &mut rx).await;

    // Cleanup terminal
    disable_raw_mode()?;
    execute!(
        terminal.backend_mut(),
        LeaveAlternateScreen,
        DisableMouseCapture
    )?;
    terminal.show_cursor()?;

    result
}

async fn run_app<B: ratatui::backend::Backend>(
    terminal: &mut Terminal<B>,
    app: &mut App,
    rx: &mut mpsc::Receiver<AppUpdate>,
) -> anyhow::Result<()>
where
    B::Error: std::error::Error + Send + Sync + 'static,
{
    loop {
        if let Ok(update) = rx.try_recv() {
            app.apply(update);
        }

        terminal.draw(|f| ui::render(f, app))?;

        if event::poll(Duration::from_millis(50))? {
            if let Event::Key(key) = event::read()? {
                match key.code {
                    KeyCode::Char('q') => return Ok(()),
                    KeyCode::Char('j') | KeyCode::Down => app.scroll_down(),
                    KeyCode::Char('k') | KeyCode::Up => app.scroll_up(),
                    KeyCode::Char('r') => {
                        if let Some(update) = poll_data().await {
                            app.apply(update);
                        }
                    }
                    KeyCode::Char('e') => app.open_escalation(),
                    _ => {}
                }
            }
        }
    }
}
