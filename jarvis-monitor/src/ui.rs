// src/ui.rs — Ratatui four-pane layout rendering

use ratatui::{
    Frame,
    layout::{Constraint, Direction, Layout, Rect},
    style::{Color, Modifier, Style},
    text::{Line, Span},
    widgets::{Block, Borders, Cell, Gauge, List, ListItem, Paragraph, Row, Table, Tabs},
};
use crate::app::App;

/// Unicode sparkline characters for latency history
const SPARK_CHARS: &[char] = &[' ', '▁', '▂', '▃', '▄', '▅', '▆', '▇', '█'];

fn sparkline(history: &[u64]) -> String {
    if history.is_empty() {
        return "─".repeat(10);
    }
    let max = *history.iter().max().unwrap_or(&1).max(&1);
    history.iter().map(|&v| {
        let idx = ((v as f64 / max as f64) * (SPARK_CHARS.len() - 1) as f64) as usize;
        SPARK_CHARS[idx.min(SPARK_CHARS.len() - 1)]
    }).collect()
}

pub fn render(f: &mut Frame, app: &mut App) {
    let area = f.area();

    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(3), Constraint::Min(0)])
        .split(area);

    render_tabs(f, app, chunks[0]);

    match app.active_tab {
        crate::app::Tab::Dashboard => render_dashboard(f, app, chunks[1]),
        crate::app::Tab::Security => render_security(f, app, chunks[1]),
        crate::app::Tab::ERS => render_ers(f, app, chunks[1]),
        crate::app::Tab::IDE => render_ide(f, app, chunks[1]),
    }
}

fn render_tabs(f: &mut Frame, app: &App, area: Rect) {
    let titles = vec!["Dashboard", "Security", "ERS", "IDE"];
    
    let tabs = Tabs::new(titles)
        .block(Block::default().borders(Borders::BOTTOM).title(" Jarvis Monitor v2 "))
        .select(app.active_tab as usize)
        .highlight_style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
        .divider("|");
    
    f.render_widget(tabs, area);
}

fn render_dashboard(f: &mut Frame, app: &mut App, area: Rect) {
    // Outer: top half / bottom half
    let rows = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(area);

    // Top: services | active task
    let top_cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(55), Constraint::Percentage(45)])
        .split(rows[0]);

    // Bottom: RAM/system | events
    let bottom_cols = Layout::default()
        .direction(Direction::Horizontal)
        .constraints([Constraint::Percentage(30), Constraint::Percentage(70)])
        .split(rows[1]);

    render_services(f, app, top_cols[0]);
    render_active_task(f, app, top_cols[1]);
    render_system(f, app, bottom_cols[0]);
    render_events(f, app, bottom_cols[1]);
}

fn render_security(f: &mut Frame, _app: &App, area: Rect) {
    let block = Block::default().borders(Borders::ALL).title(" Security Audit Log ");
    let para = Paragraph::new("Loading from security_audit.db...")
        .block(block)
        .style(Style::default().fg(Color::Yellow));
    f.render_widget(para, area);
}

fn render_ers(f: &mut Frame, _app: &App, area: Rect) {
    let block = Block::default().borders(Borders::ALL).title(" ERS Reasoning Chains ");
    let para = Paragraph::new("No active chains.")
        .block(block)
        .style(Style::default().fg(Color::Magenta));
    f.render_widget(para, area);
}

fn render_ide(f: &mut Frame, _app: &App, area: Rect) {
    let block = Block::default().borders(Borders::ALL).title(" IDE Bridge Status ");
    let para = Paragraph::new("LSP port 8002: Active\nHTTP port 8001: Active")
        .block(block)
        .style(Style::default().fg(Color::Cyan));
    f.render_widget(para, area);
}

fn render_services(f: &mut Frame, app: &App, area: Rect) {
    let header = Row::new(vec![
        Cell::from("Service").style(Style::default().add_modifier(Modifier::BOLD)),
        Cell::from("State").style(Style::default().add_modifier(Modifier::BOLD)),
        Cell::from("History").style(Style::default().add_modifier(Modifier::BOLD)),
    ]);

    let rows: Vec<Row> = app.services.iter().map(|s| {
        let (state_str, state_color) = if s.active {
            ("● active", Color::Green)
        } else {
            ("○ stopped", Color::Red)
        };
        let short_name = s.name.replace("jarvis-", "").replace('-', " ");
        Row::new(vec![
            Cell::from(short_name),
            Cell::from(state_str).style(Style::default().fg(state_color)),
            Cell::from(sparkline(&s.history)),
        ])
    }).collect();

    let widths = [Constraint::Min(18), Constraint::Min(10), Constraint::Min(12)];
    let table = Table::new(rows, widths)
        .header(header.style(Style::default().bg(Color::Cyan).fg(Color::Black).add_modifier(Modifier::BOLD)))
        .block(Block::default().borders(Borders::ALL).title(" Services ").style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)))
        .row_highlight_style(Style::default().add_modifier(Modifier::BOLD).fg(Color::White).bg(Color::Cyan));

    f.render_widget(table, area);
}

fn render_active_task(f: &mut Frame, app: &App, area: Rect) {
    let content = match &app.active_task {
        Some(task) => format!("Latest:\n{}", task),
        None => "(no recent activity)".into(),
    };

    let para = Paragraph::new(content)
        .block(Block::default().borders(Borders::ALL).title(" Active Task ").style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)))
        .style(Style::default().fg(Color::Cyan).add_modifier(Modifier::BOLD))
        .wrap(ratatui::widgets::Wrap { trim: true });

    f.render_widget(para, area);
}

fn render_system(f: &mut Frame, app: &App, area: Rect) {
    let chunks = Layout::default()
        .direction(Direction::Vertical)
        .constraints([Constraint::Length(4), Constraint::Length(4), Constraint::Length(4), Constraint::Min(0)])
        .split(area);

    // RAM gauge
    let ram_ratio = if app.ram.total_gb > 0.0 {
        (app.ram.used_gb / app.ram.total_gb).min(1.0)
    } else { 0.0 };
    let ram_label = format!("{:.1}/{:.1} GB", app.ram.used_gb, app.ram.total_gb);
    let ram_color = if ram_ratio > 0.85 { Color::Red } else if ram_ratio > 0.6 { Color::Yellow } else { Color::Green };
    let ram_gauge = Gauge::default()
        .block(Block::default().borders(Borders::ALL).title(" RAM ").style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)))
        .gauge_style(Style::default().fg(ram_color).bg(Color::Gray))
        .ratio(ram_ratio)
        .label(ram_label);
    f.render_widget(ram_gauge, chunks[0]);

    // Swap gauge
    let swap_ratio = if app.ram.swap_total_gb > 0.0 {
        (app.ram.swap_used_gb / app.ram.swap_total_gb).min(1.0)
    } else { 0.0 };
    let swap_label = format!("{:.1}/{:.1} GB", app.ram.swap_used_gb, app.ram.swap_total_gb);
    let swap_gauge = Gauge::default()
        .block(Block::default().borders(Borders::ALL).title(" Swap ").style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)))
        .gauge_style(Style::default().fg(Color::Magenta).bg(Color::Gray))
        .ratio(swap_ratio)
        .label(swap_label);
    f.render_widget(swap_gauge, chunks[1]);

    // Budget gauge
    let budget_ratio = if app.budget.daily_limit > 0 {
        (app.budget.tokens_used as f64 / app.budget.daily_limit as f64).min(1.0)
    } else { 0.0 };
    let budget_label = format!("{} / {} tk | ${:.2}", app.budget.tokens_used, app.budget.daily_limit, app.budget.cost_usd);
    let budget_color = if budget_ratio > 0.85 { Color::Red } else if budget_ratio > 0.6 { Color::Yellow } else { Color::Green };
    let budget_gauge = Gauge::default()
        .block(Block::default().borders(Borders::ALL).title(" Budget ").style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)))
        .gauge_style(Style::default().fg(budget_color).bg(Color::Gray))
        .ratio(budget_ratio)
        .label(budget_label);
    f.render_widget(budget_gauge, chunks[2]);

    // Key hints
    let hints = Paragraph::new("q:quit  j/k:scroll  r:refresh  e:open")
        .block(Block::default().borders(Borders::ALL).title(" Keys ").style(Style::default().fg(Color::Gray).add_modifier(Modifier::BOLD)))
        .style(Style::default().fg(Color::Gray).add_modifier(Modifier::BOLD));
    f.render_widget(hints, chunks[3]);
}

fn render_events(f: &mut Frame, app: &App, area: Rect) {
    let visible_events = app.events.iter()
        .skip(app.scroll_offset)
        .take(area.height as usize - 2)
        .map(|e| {
            let color = match e.source.as_str() {
                "coding_agent" => Color::Cyan, 
                "ingest" => Color::Green, 
                "optimizer" => Color::Magenta,
                "health_monitor" => Color::Yellow, 
                s if s.contains("error") || s.contains("fail") => Color::Red,
                _ => Color::White,
            };
            ListItem::new(Line::from(vec![
                Span::styled(format!("{} ", &e.ts.get(..19).unwrap_or(&e.ts)), Style::default().fg(Color::DarkGray)),
                Span::styled(format!("[{}] ", e.source), Style::default().fg(color).add_modifier(Modifier::BOLD)),
                Span::styled(&e.event, Style::default().fg(Color::White)),
            ]))
        })
        .collect::<Vec<_>>();

    let scroll_hint = if app.events.len() > (area.height as usize - 2) {
        format!(" Events ({}/{}) ", app.scroll_offset + 1, app.events.len())
    } else {
        format!(" Events ({}) ", app.events.len())
    };

    let list = List::new(visible_events)
        .block(Block::default().borders(Borders::ALL).title(scroll_hint).style(Style::default().fg(Color::White).add_modifier(Modifier::BOLD)));

    f.render_widget(list, area);
}
