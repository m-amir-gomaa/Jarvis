// src/data.rs — DB polling and system metrics

use std::process::Command;
use rusqlite::{Connection, Result as SqlResult};
use crate::app::{AppUpdate, JarvisEvent, RamUsage, ServiceStatus, BudgetInfo};
use chrono::Utc;

fn events_db_path() -> std::path::PathBuf {
    let vault = std::env::var("VAULT_ROOT")
        .unwrap_or_else(|_| "/THE_VAULT/jarvis".to_string());
    std::path::PathBuf::from(vault).join("logs").join("events.db")
}

fn query_recent_events() -> Vec<JarvisEvent> {
    let db_path = events_db_path();
    let Ok(conn) = Connection::open(&db_path) else {
        return vec![];
    };
    let _ = conn.execute("PRAGMA query_only = true", []); // FIX-RUST-1
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
    // Look for the most recent event from "important" sources
    let important_sources = ["coding_agent", "ingest", "doc_learner", "git_monitor"];
    
    events.iter().find(|e| important_sources.contains(&e.source.as_str())).map(|e| {
        let mut details = e.details.clone();
        // Simple JSON cleanup for display
        details = details.replace("{", "").replace("}", "").replace("\"", "");
        if details.len() > 50 {
            details = format!("{}...", &details[..47]);
        }
        
        if details.is_empty() {
            format!("[{}] {}", e.source, e.event)
        } else {
            format!("[{}] {}: {}", e.source, e.event, details)
        }
    })
}

fn get_budget_info() -> BudgetInfo {
    let vault = std::env::var("VAULT_ROOT").unwrap_or_else(|_| "/THE_VAULT/jarvis".to_string());
    let db_path = std::path::PathBuf::from(vault).join("databases").join("api_usage.db");
    
    let mut info = BudgetInfo {
        tokens_used: 0,
        daily_limit: 200_000,
        cost_usd: 0.0,
        cost_limit: 2.0,
    };

    if let Ok(conn) = Connection::open(&db_path) {
        let _ = conn.execute("PRAGMA query_only = true", []); // FIX-RUST-1
        let today = Utc::now().format("%Y-%m-%d").to_string();
        if let Ok(mut stmt) = conn.prepare("SELECT SUM(prompt_tokens + output_tokens), SUM(cost_usd) FROM api_usage WHERE date(ts) = ?") {
            if let Ok(mut rows) = stmt.query([today]) {
                if let Ok(Some(row)) = rows.next() {
                    info.tokens_used = row.get::<_, Option<i64>>(0).unwrap_or(Some(0)).unwrap_or(0);
                    info.cost_usd = row.get::<_, Option<f64>>(1).unwrap_or(Some(0.0)).unwrap_or(0.0);
                }
            }
        }
    }
    info
}


pub async fn poll_data() -> Option<AppUpdate> {
    let service_names = ["jarvis-ingest", "jarvis-health-monitor", "jarvis-git-monitor", "jarvis-coding-agent"];

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
    let budget = get_budget_info();

    Some(AppUpdate { services, events, ram, active_task, budget })
}
