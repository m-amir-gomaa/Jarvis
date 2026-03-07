// src/app.rs — App state and update types

use std::process::Command;

#[derive(Debug, Clone, Copy, PartialEq, Eq)]
pub enum Tab {
    Dashboard,
    Security,
    ERS,
    IDE,
}

#[derive(Debug, Clone, Default)]
pub struct ServiceStatus {
    pub name: String,
    pub active: bool,
    pub latency_ms: u64,
    pub history: Vec<u64>, // last 20 latency samples for sparkline
}

#[derive(Debug, Clone, Default)]
pub struct JarvisEvent {
    pub ts: String,
    pub source: String,
    pub event: String,
    pub details: String,
}

#[derive(Debug, Clone, Default)]
pub struct RamUsage {
    pub used_gb: f64,
    pub total_gb: f64,
    pub swap_used_gb: f64,
    pub swap_total_gb: f64,
}

#[derive(Debug, Clone, Default)]
pub struct BudgetInfo {
    pub tokens_used: i64,
    pub daily_limit: i64,
    pub cost_usd: f64,
    pub cost_limit: f64,
}

#[derive(Debug, Clone, Default)]
pub struct AppUpdate {
    pub services: Vec<ServiceStatus>,
    pub events: Vec<JarvisEvent>, // newest first
    pub ram: RamUsage,
    pub active_task: Option<String>,
    pub budget: BudgetInfo,
}

pub struct App {
    pub services: Vec<ServiceStatus>,
    pub events: Vec<JarvisEvent>,
    pub ram: RamUsage,
    pub active_task: Option<String>,
    pub scroll_offset: usize,
    pub budget: BudgetInfo,
    pub active_tab: Tab,
}

impl App {
    pub fn new() -> Self {
        Self {
            services: vec![
                ServiceStatus { name: "jarvis-health-monitor".into(), ..Default::default() },
                ServiceStatus { name: "jarvis-git-monitor".into(), ..Default::default() },
                ServiceStatus { name: "jarvis-coding-agent".into(), ..Default::default() },
                ServiceStatus { name: "ollama".into(), ..Default::default() },
            ],
            events: vec![],
            ram: RamUsage::default(),
            active_task: None,
            scroll_offset: 0,
            budget: BudgetInfo::default(),
            active_tab: Tab::Dashboard,
        }
    }

    pub fn apply(&mut self, update: AppUpdate) {
        self.services = update.services;
        self.events = update.events;
        self.ram = update.ram;
        self.active_task = update.active_task;
        self.budget = update.budget;
    }

    pub fn scroll_down(&mut self) {
        if self.scroll_offset + 1 < self.events.len() {
            self.scroll_offset += 1;
        }
    }

    pub fn scroll_up(&mut self) {
        if self.scroll_offset > 0 {
            self.scroll_offset -= 1;
        }
    }

    pub fn open_escalation(&self) {
        // Open the most recent 'escalated' event file in $EDITOR
        if let Some(event) = self.events.iter().find(|e| e.event.contains("escalat")) {
            let path = format!("/THE_VAULT/jarvis/review/{}.md", event.ts.replace(':', "-"));
            let editor = std::env::var("EDITOR").unwrap_or("nvim".into());
            let _ = Command::new(editor).arg(&path).spawn();
        }
    }
}
