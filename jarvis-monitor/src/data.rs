// src/data.rs — DB polling and system metrics

use std::process::Command;
use rusqlite::{Connection, Result as SqlResult};
use crate::app::{AppUpdate, JarvisEvent, RamUsage, ServiceStatus};

const EVENTS_DB: &str = "/THE_VAULT/jarvis/logs/events.db";

fn query_recent_events() -> Vec<JarvisEvent> {
    let Ok(conn) = Connection::open(EVENTS_DB) else {
        return vec![];
    };
    let Ok(mut stmt) = conn.prepare(
        "SELECT ts, source, event, details FROM events ORDER BY ts DESC LIMIT 50"
    ) else {
        return vec![];
    };
    stmt.query_map([], |row| {
        Ok(JarvisEvent {
            ts: row.get(0)?,
            source: row.get(1)?,
            event: row.get(2)?,
            details: row.get(3)?,
        })
    })
    .map(|rows| rows.filter_map(|r| r.ok()).collect())
    .unwrap_or_default()
}

fn check_service_active(name: &str) -> bool {
    Command::new("systemctl")
        .args(["--user", "is-active", &format!("{}.service", name)])
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "active")
        .unwrap_or(false)
}

fn check_ollama_active() -> bool {
    Command::new("systemctl")
        .args(["is-active", "ollama.service"])
        .output()
        .map(|o| String::from_utf8_lossy(&o.stdout).trim() == "active")
        .unwrap_or(false)
}

fn get_ram_usage() -> RamUsage {
    let Ok(output) = Command::new("free").arg("--bytes").output() else {
        return RamUsage::default();
    };
    let text = String::from_utf8_lossy(&output.stdout);
    let mut ram = RamUsage::default();
    for line in text.lines() {
        let parts: Vec<&str> = line.split_whitespace().collect();
        if parts.first() == Some(&"Mem:") && parts.len() >= 3 {
            ram.total_gb = parts[1].parse::<f64>().unwrap_or(0.0) / 1_073_741_824.0;
            ram.used_gb = parts[2].parse::<f64>().unwrap_or(0.0) / 1_073_741_824.0;
        }
        if parts.first() == Some(&"Swap:") && parts.len() >= 3 {
            ram.swap_total_gb = parts[1].parse::<f64>().unwrap_or(0.0) / 1_073_741_824.0;
            ram.swap_used_gb = parts[2].parse::<f64>().unwrap_or(0.0) / 1_073_741_824.0;
        }
    }
    ram
}

fn get_active_task(events: &[JarvisEvent]) -> Option<String> {
    events.first().map(|e| format!("[{}] {}", e.source, e.event))
}

pub async fn poll_data() -> Option<AppUpdate> {
    let service_names = ["jarvis-health-monitor", "jarvis-git-monitor", "jarvis-coding-agent"];

    let services: Vec<ServiceStatus> = service_names.iter().map(|name| {
        ServiceStatus {
            name: name.to_string(),
            active: check_service_active(name),
            latency_ms: 0,
            history: vec![],
        }
    }).chain(std::iter::once(ServiceStatus {
        name: "ollama".to_string(),
        active: check_ollama_active(),
        latency_ms: 0,
        history: vec![],
    })).collect();

    let events = query_recent_events();
    let active_task = get_active_task(&events);
    let ram = get_ram_usage();

    Some(AppUpdate { services, events, ram, active_task })
}
