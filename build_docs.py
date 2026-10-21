#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Build Script for Unified NYC Taxi Documentation Hub
Generates a comprehensive, interactive HTML documentation file at docs/index.html
incorporating all markdown documentation from taxi_lakehouse and taxi_streaming.
"""

import os
import sys

def generate_html():
    html_content = r"""<!DOCTYPE html>
<html lang="vi" data-theme="dark">
<head>
  <meta charset="UTF-8">
  <meta name="viewport" content="width=device-width, initial-scale=1.0">
  <title>NYC Taxi Platform Intelligence | Cẩm Nang Kiến Trúc & Báo Cáo Hợp Nhất</title>
  <meta name="description" content="Tài liệu kiến trúc toàn diện và phân tích dữ liệu cho 2 dự án: NYC Taxi Lakehouse Pipeline (Medallion, Spark, Delta Lake, Trino, LightGBM) và NYC Taxi Real-Time Streaming Pipeline (Kafka, Flink, Redis, FastAPI, Deck.gl 3D).">
  
  <!-- Google Fonts -->
  <link rel="preconnect" href="https://fonts.googleapis.com">
  <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin>
  <link href="https://fonts.googleapis.com/css2?family=JetBrains+Mono:ital,wght@0,300;0,400;0,500;0,600;0,700;1,400&family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap" rel="stylesheet">

  <style>
    /* ==========================================================================
       1. DESIGN TOKENS & RESET
       ========================================================================== */
    :root {
      /* Dark Theme (Default) */
      --bg-base: #020B18;
      --bg-surface: #071326;
      --bg-panel: rgba(10, 22, 40, 0.88);
      --bg-card: rgba(15, 27, 49, 0.75);
      --bg-card-hover: rgba(22, 38, 68, 0.9);
      --bg-code: #030811;
      
      --border-subtle: rgba(56, 189, 248, 0.16);
      --border-medium: rgba(56, 189, 248, 0.32);
      --border-glow: rgba(0, 245, 255, 0.45);
      
      --cyan: #00F5FF;
      --cyan-muted: rgba(0, 245, 255, 0.12);
      --sky: #38BDF8;
      --yellow: #FACC15;
      --yellow-muted: rgba(250, 204, 21, 0.12);
      --green: #22C55E;
      --green-muted: rgba(34, 197, 94, 0.12);
      --purple: #A855F7;
      --purple-muted: rgba(168, 85, 247, 0.12);
      --red: #F43F5E;
      --red-muted: rgba(244, 63, 94, 0.12);
      --amber: #F59E0B;
      
      --text-primary: #F8FAFC;
      --text-secondary: #94A3B8;
      --text-muted: #64748B;
      
      --shadow-sm: 0 2px 8px rgba(0, 0, 0, 0.3);
      --shadow-md: 0 8px 24px rgba(0, 0, 0, 0.45);
      --shadow-glow: 0 0 25px rgba(0, 245, 255, 0.2);
      --shadow-glow-yellow: 0 0 25px rgba(250, 204, 21, 0.2);
      --shadow-glow-purple: 0 0 25px rgba(168, 85, 247, 0.2);
      
      --sidebar-width: 320px;
      --header-height: 72px;
      --radius-sm: 6px;
      --radius-md: 10px;
      --radius-lg: 16px;
      --radius-full: 9999px;
      
      --transition: all 0.25s cubic-bezier(0.16, 1, 0.3, 1);
    }

    [data-theme="light"] {
      --bg-base: #F8FAFC;
      --bg-surface: #FFFFFF;
      --bg-panel: rgba(255, 255, 255, 0.95);
      --bg-card: #FFFFFF;
      --bg-card-hover: #F1F5F9;
      --bg-code: #0F172A;
      
      --border-subtle: rgba(15, 23, 42, 0.1);
      --border-medium: rgba(15, 23, 42, 0.2);
      --border-glow: rgba(2, 132, 199, 0.3);
      
      --cyan: #0284C7;
      --cyan-muted: rgba(2, 132, 199, 0.1);
      --sky: #0369A1;
      --yellow: #D97706;
      --yellow-muted: rgba(217, 119, 6, 0.1);
      --green: #15803D;
      --green-muted: rgba(21, 128, 61, 0.1);
      --purple: #7E22CE;
      --purple-muted: rgba(126, 34, 206, 0.1);
      --red: #BE123C;
      --red-muted: rgba(190, 18, 60, 0.1);
      
      --text-primary: #0F172A;
      --text-secondary: #475569;
      --text-muted: #64748B;
      
      --shadow-sm: 0 1px 3px rgba(0, 0, 0, 0.08);
      --shadow-md: 0 4px 16px rgba(0, 0, 0, 0.08);
      --shadow-glow: 0 0 20px rgba(2, 132, 199, 0.15);
    }

    *, *::before, *::after {
      box-sizing: border-box;
      margin: 0;
      padding: 0;
    }

    html {
      scroll-behavior: smooth;
      font-size: 15px;
    }

    body {
      font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
      background-color: var(--bg-base);
      color: var(--text-primary);
      line-height: 1.65;
      min-height: 100vh;
      display: flex;
      flex-direction: column;
      overflow-x: hidden;
      transition: background-color 0.3s ease, color 0.3s ease;
    }

    /* Reading Progress Bar */
    #progress-bar {
      position: fixed;
      top: 0;
      left: 0;
      height: 3px;
      width: 0%;
      background: linear-gradient(90deg, var(--cyan), var(--yellow), var(--purple));
      z-index: 1000;
      transition: width 0.1s ease-out;
      box-shadow: 0 0 10px var(--cyan);
    }

    /* Scrollbar */
    ::-webkit-scrollbar {
      width: 8px;
      height: 8px;
    }
    ::-webkit-scrollbar-track {
      background: var(--bg-base);
    }
    ::-webkit-scrollbar-thumb {
      background: rgba(56, 189, 248, 0.25);
      border-radius: var(--radius-full);
    }
    ::-webkit-scrollbar-thumb:hover {
      background: var(--cyan);
    }

    /* Code styling */
    code, pre, .font-mono {
      font-family: 'JetBrains Mono', monospace;
    }

    /* ==========================================================================
       2. TOP NAVBAR
       ========================================================================== */
    .top-header {
      position: sticky;
      top: 0;
      height: var(--header-height);
      background: var(--bg-panel);
      backdrop-filter: blur(16px);
      -webkit-backdrop-filter: blur(16px);
      border-bottom: 1px solid var(--border-subtle);
      z-index: 900;
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 2rem;
      transition: var(--transition);
    }

    .brand-group {
      display: flex;
      align-items: center;
      gap: 1rem;
    }

    .brand-logo {
      display: flex;
      align-items: center;
      justify-content: center;
      width: 44px;
      height: 44px;
      border-radius: var(--radius-md);
      background: linear-gradient(135deg, rgba(0, 245, 255, 0.2), rgba(168, 85, 247, 0.2));
      border: 1px solid var(--border-medium);
      color: var(--cyan);
      box-shadow: var(--shadow-glow);
    }

    .brand-logo svg {
      width: 24px;
      height: 24px;
    }

    .brand-info h1 {
      font-size: 1.15rem;
      font-weight: 800;
      letter-spacing: -0.02em;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      background: linear-gradient(90deg, var(--text-primary), var(--cyan));
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .brand-info p {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 500;
    }

    .header-actions {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .badge-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.35rem;
      padding: 0.25rem 0.65rem;
      border-radius: var(--radius-full);
      font-size: 0.75rem;
      font-weight: 600;
      letter-spacing: 0.02em;
      border: 1px solid transparent;
    }

    .badge-cyan {
      background: var(--cyan-muted);
      color: var(--cyan);
      border-color: rgba(0, 245, 255, 0.3);
    }
    .badge-yellow {
      background: var(--yellow-muted);
      color: var(--yellow);
      border-color: rgba(250, 204, 21, 0.3);
    }
    .badge-purple {
      background: var(--purple-muted);
      color: var(--purple);
      border-color: rgba(168, 85, 247, 0.3);
    }
    .badge-green {
      background: var(--green-muted);
      color: var(--green);
      border-color: rgba(34, 197, 94, 0.3);
    }

    .btn-icon {
      width: 38px;
      height: 38px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-md);
      background: var(--bg-surface);
      border: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      cursor: pointer;
      transition: var(--transition);
    }

    .btn-icon:hover {
      color: var(--cyan);
      border-color: var(--cyan);
      background: var(--cyan-muted);
      transform: translateY(-1px);
    }

    .btn-icon svg {
      width: 18px;
      height: 18px;
    }

    .mobile-menu-btn {
      display: none;
    }

    /* ==========================================================================
       3. APP LAYOUT WITH BOOKMARK SIDEBAR
       ========================================================================== */
    .app-layout {
      display: flex;
      width: 100%;
      min-height: calc(100vh - var(--header-height));
      position: relative;
    }

    /* Bookmark Navigation Sidebar */
    .sidebar {
      width: var(--sidebar-width);
      height: calc(100vh - var(--header-height));
      position: sticky;
      top: var(--header-height);
      background: var(--bg-surface);
      border-right: 1px solid var(--border-subtle);
      overflow-y: auto;
      padding: 1.5rem 1rem;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      flex-shrink: 0;
      transition: var(--transition);
      z-index: 850;
    }

    .sidebar-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0 0.5rem;
    }

    .sidebar-title {
      font-size: 0.85rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: var(--cyan);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .search-box {
      position: relative;
      width: 100%;
    }

    .search-input {
      width: 100%;
      padding: 0.65rem 0.85rem 0.65rem 2.25rem;
      border-radius: var(--radius-md);
      background: var(--bg-base);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      font-size: 0.85rem;
      font-family: inherit;
      outline: none;
      transition: var(--transition);
    }

    .search-input:focus {
      border-color: var(--cyan);
      box-shadow: 0 0 12px var(--cyan-muted);
    }

    .search-icon {
      position: absolute;
      left: 0.75rem;
      top: 50%;
      transform: translateY(-50%);
      color: var(--text-muted);
      pointer-events: none;
      width: 16px;
      height: 16px;
    }

    /* Nav Links & Bookmarks */
    .nav-sections {
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
    }

    .nav-group-title {
      font-size: 0.72rem;
      text-transform: uppercase;
      font-weight: 700;
      letter-spacing: 0.08em;
      color: var(--text-muted);
      padding: 0.25rem 0.5rem;
      display: flex;
      align-items: center;
      justify-content: space-between;
    }

    .nav-list {
      list-style: none;
      display: flex;
      flex-direction: column;
      gap: 0.2rem;
    }

    .nav-item a {
      display: flex;
      align-items: center;
      gap: 0.65rem;
      padding: 0.5rem 0.75rem;
      border-radius: var(--radius-sm);
      color: var(--text-secondary);
      text-decoration: none;
      font-size: 0.85rem;
      font-weight: 500;
      border-left: 2px solid transparent;
      transition: var(--transition);
      line-height: 1.3;
    }

    .nav-item a:hover {
      color: var(--text-primary);
      background: rgba(56, 189, 248, 0.08);
      border-left-color: var(--sky);
      transform: translateX(2px);
    }

    .nav-item a.active {
      color: var(--cyan);
      background: var(--cyan-muted);
      border-left-color: var(--cyan);
      font-weight: 600;
      box-shadow: inset 0 0 15px rgba(0, 245, 255, 0.05);
    }

    .nav-item a svg {
      width: 16px;
      height: 16px;
      flex-shrink: 0;
    }

    .nav-sub-list {
      list-style: none;
      padding-left: 1.75rem;
      display: flex;
      flex-direction: column;
      gap: 0.15rem;
      margin-top: 0.15rem;
    }

    .nav-sub-item a {
      padding: 0.35rem 0.5rem;
      font-size: 0.78rem;
      color: var(--text-muted);
      border-left: 1px dashed var(--border-subtle);
      border-radius: 0 var(--radius-sm) var(--radius-sm) 0;
    }

    .nav-sub-item a:hover {
      color: var(--sky);
      border-left-color: var(--sky);
      background: rgba(56, 189, 248, 0.05);
    }

    .nav-sub-item a.active {
      color: var(--cyan);
      border-left-color: var(--cyan);
      font-weight: 600;
    }

    /* Main Content Container */
    .main-content {
      flex: 1;
      max-width: calc(100% - var(--sidebar-width));
      padding: 2.5rem 3.5rem;
      overflow-y: visible;
    }

    /* ==========================================================================
       4. HERO BANNER & STATS
       ========================================================================== */
    .hero-banner {
      background: linear-gradient(135deg, rgba(7, 19, 38, 0.95), rgba(15, 27, 49, 0.85));
      border: 1px solid var(--border-medium);
      border-radius: var(--radius-lg);
      padding: 2.5rem;
      margin-bottom: 2.5rem;
      position: relative;
      overflow: hidden;
      box-shadow: var(--shadow-md);
    }

    .hero-banner::after {
      content: '';
      position: absolute;
      top: -50%;
      right: -20%;
      width: 400px;
      height: 400px;
      background: radial-gradient(circle, rgba(0, 245, 255, 0.15), transparent 70%);
      pointer-events: none;
    }

    .hero-tag {
      display: inline-flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 0.8rem;
      font-weight: 700;
      color: var(--cyan);
      text-transform: uppercase;
      letter-spacing: 0.05em;
      margin-bottom: 0.75rem;
    }

    .hero-title {
      font-size: 2.25rem;
      font-weight: 800;
      line-height: 1.25;
      letter-spacing: -0.03em;
      margin-bottom: 1rem;
      background: linear-gradient(135deg, #FFFFFF 30%, var(--cyan) 100%);
      -webkit-background-clip: text;
      -webkit-text-fill-color: transparent;
    }

    .hero-desc {
      font-size: 1.05rem;
      color: var(--text-secondary);
      max-width: 850px;
      margin-bottom: 2rem;
      line-height: 1.6;
    }

    .hero-metrics {
      display: grid;
      grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
      gap: 1.25rem;
      padding-top: 1.5rem;
      border-top: 1px solid var(--border-subtle);
    }

    .metric-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      padding: 1.25rem;
      transition: var(--transition);
      position: relative;
      overflow: hidden;
    }

    .metric-card:hover {
      border-color: var(--border-glow);
      transform: translateY(-3px);
      box-shadow: var(--shadow-glow);
    }

    .metric-card::before {
      content: '';
      position: absolute;
      top: 0;
      left: 0;
      width: 3px;
      height: 100%;
    }

    .metric-cyan::before { background: var(--cyan); }
    .metric-yellow::before { background: var(--yellow); }
    .metric-purple::before { background: var(--purple); }
    .metric-green::before { background: var(--green); }

    .metric-value {
      font-family: 'JetBrains Mono', monospace;
      font-size: 1.75rem;
      font-weight: 700;
      line-height: 1.2;
      margin-bottom: 0.25rem;
      color: var(--text-primary);
    }

    .metric-label {
      font-size: 0.8rem;
      color: var(--text-muted);
      font-weight: 600;
      text-transform: uppercase;
      letter-spacing: 0.04em;
    }

    .metric-sub {
      font-size: 0.75rem;
      color: var(--text-secondary);
      margin-top: 0.35rem;
    }

    /* ==========================================================================
       5. CONTENT SECTIONS & TYPOGRAPHY
       ========================================================================== */
    .section-block {
      margin-bottom: 3.5rem;
      scroll-margin-top: calc(var(--header-height) + 1.5rem);
    }

    .section-header {
      display: flex;
      align-items: center;
      gap: 0.85rem;
      margin-bottom: 1.25rem;
      padding-bottom: 0.75rem;
      border-bottom: 1px solid var(--border-subtle);
    }

    .section-icon {
      width: 36px;
      height: 36px;
      display: flex;
      align-items: center;
      justify-content: center;
      border-radius: var(--radius-md);
      background: var(--cyan-muted);
      color: var(--cyan);
      border: 1px solid var(--border-medium);
      flex-shrink: 0;
    }

    .section-header h2 {
      font-size: 1.6rem;
      font-weight: 700;
      letter-spacing: -0.02em;
      color: var(--text-primary);
    }

    .subsection-header {
      display: flex;
      align-items: center;
      gap: 0.5rem;
      font-size: 1.25rem;
      font-weight: 600;
      margin: 2rem 0 1rem 0;
      color: var(--sky);
      scroll-margin-top: calc(var(--header-height) + 2rem);
    }

    p {
      margin-bottom: 1rem;
      color: var(--text-secondary);
      line-height: 1.7;
    }

    strong {
      color: var(--text-primary);
      font-weight: 600;
    }

    /* Alerts / Callouts */
    .callout {
      border-radius: var(--radius-md);
      padding: 1.25rem 1.5rem;
      margin: 1.5rem 0;
      border-left: 4px solid;
      background: var(--bg-card);
      position: relative;
    }

    .callout-title {
      font-weight: 700;
      font-size: 0.95rem;
      display: flex;
      align-items: center;
      gap: 0.5rem;
      margin-bottom: 0.5rem;
    }

    .callout-info {
      border-left-color: var(--cyan);
      background: rgba(0, 245, 255, 0.04);
      border: 1px solid rgba(0, 245, 255, 0.2);
      border-left-width: 4px;
    }
    .callout-info .callout-title { color: var(--cyan); }

    .callout-warning {
      border-left-color: var(--yellow);
      background: rgba(250, 204, 21, 0.04);
      border: 1px solid rgba(250, 204, 21, 0.2);
      border-left-width: 4px;
    }
    .callout-warning .callout-title { color: var(--yellow); }

    .callout-success {
      border-left-color: var(--green);
      background: rgba(34, 197, 94, 0.04);
      border: 1px solid rgba(34, 197, 94, 0.2);
      border-left-width: 4px;
    }
    .callout-success .callout-title { color: var(--green); }

    .callout-danger {
      border-left-color: var(--red);
      background: rgba(244, 63, 94, 0.04);
      border: 1px solid rgba(244, 63, 94, 0.2);
      border-left-width: 4px;
    }
    .callout-danger .callout-title { color: var(--red); }

    /* Tables */
    .table-container {
      width: 100%;
      overflow-x: auto;
      margin: 1.5rem 0;
      border-radius: var(--radius-md);
      border: 1px solid var(--border-subtle);
      background: var(--bg-card);
      box-shadow: var(--shadow-sm);
    }

    table {
      width: 100%;
      border-collapse: collapse;
      text-align: left;
      font-size: 0.88rem;
    }

    th {
      background: rgba(7, 19, 38, 0.9);
      color: var(--cyan);
      font-weight: 700;
      padding: 0.9rem 1.1rem;
      border-bottom: 1px solid var(--border-medium);
      text-transform: uppercase;
      font-size: 0.75rem;
      letter-spacing: 0.05em;
    }

    td {
      padding: 0.85rem 1.1rem;
      border-bottom: 1px solid var(--border-subtle);
      color: var(--text-secondary);
      vertical-align: top;
    }

    tr:last-child td {
      border-bottom: none;
    }

    tr:hover td {
      background: rgba(56, 189, 248, 0.03);
      color: var(--text-primary);
    }

    /* Comparison Dual Grid */
    .comparison-grid {
      display: grid;
      grid-template-columns: 1fr 1fr;
      gap: 1.5rem;
      margin: 1.5rem 0;
    }

    .project-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-lg);
      padding: 1.75rem;
      position: relative;
      display: flex;
      flex-direction: column;
      gap: 1.25rem;
      transition: var(--transition);
    }

    .project-card:hover {
      border-color: var(--border-glow);
      transform: translateY(-4px);
      box-shadow: var(--shadow-md);
    }

    .project-card-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      border-bottom: 1px solid var(--border-subtle);
      padding-bottom: 1rem;
    }

    .project-badge-title {
      display: flex;
      align-items: center;
      gap: 0.75rem;
    }

    .project-badge-title h3 {
      font-size: 1.2rem;
      font-weight: 700;
      color: var(--text-primary);
    }

    .tech-tags {
      display: flex;
      flex-wrap: wrap;
      gap: 0.4rem;
    }

    .tech-tag {
      font-family: 'JetBrains Mono', monospace;
      font-size: 0.72rem;
      padding: 0.2rem 0.5rem;
      border-radius: var(--radius-sm);
      background: rgba(56, 189, 248, 0.1);
      color: var(--sky);
      border: 1px solid rgba(56, 189, 248, 0.2);
    }

    /* Code Blocks */
    .code-container {
      position: relative;
      margin: 1.25rem 0;
      border-radius: var(--radius-md);
      background: var(--bg-code);
      border: 1px solid var(--border-subtle);
      overflow: hidden;
    }

    .code-header {
      display: flex;
      align-items: center;
      justify-content: space-between;
      padding: 0.5rem 1rem;
      background: rgba(255, 255, 255, 0.03);
      border-bottom: 1px solid rgba(255, 255, 255, 0.05);
      font-size: 0.75rem;
      color: var(--text-muted);
      font-family: 'JetBrains Mono', monospace;
    }

    .btn-copy {
      background: transparent;
      border: none;
      color: var(--text-muted);
      cursor: pointer;
      display: flex;
      align-items: center;
      gap: 0.35rem;
      font-size: 0.75rem;
      font-family: inherit;
      padding: 0.25rem 0.5rem;
      border-radius: var(--radius-sm);
      transition: var(--transition);
    }

    .btn-copy:hover {
      color: var(--cyan);
      background: var(--cyan-muted);
    }

    pre {
      padding: 1.2rem 1.25rem;
      overflow-x: auto;
      font-size: 0.85rem;
      line-height: 1.6;
      color: #E2E8F0;
    }

    /* Tabs Component */
    .tabs-wrapper {
      margin: 1.5rem 0;
    }

    .tab-nav {
      display: flex;
      gap: 0.5rem;
      border-bottom: 1px solid var(--border-subtle);
      margin-bottom: 1.25rem;
    }

    .tab-btn {
      padding: 0.65rem 1.2rem;
      background: transparent;
      border: none;
      border-bottom: 2px solid transparent;
      color: var(--text-muted);
      font-family: inherit;
      font-size: 0.9rem;
      font-weight: 600;
      cursor: pointer;
      transition: var(--transition);
      display: flex;
      align-items: center;
      gap: 0.5rem;
    }

    .tab-btn:hover {
      color: var(--text-primary);
    }

    .tab-btn.active {
      color: var(--cyan);
      border-bottom-color: var(--cyan);
    }

    .tab-pane {
      display: none;
    }

    .tab-pane.active {
      display: block;
      animation: fadeIn 0.3s ease;
    }

    @keyframes fadeIn {
      from { opacity: 0; transform: translateY(4px); }
      to { opacity: 1; transform: translateY(0); }
    }

    /* Report Image Gallery Grid */
    .gallery-grid {
      display: grid;
      grid-template-columns: repeat(auto-fill, minmax(360px, 1fr));
      gap: 1.5rem;
      margin: 1.5rem 0;
    }

    .gallery-card {
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      border-radius: var(--radius-md);
      overflow: hidden;
      display: flex;
      flex-direction: column;
      transition: var(--transition);
    }

    .gallery-card:hover {
      border-color: var(--cyan);
      transform: translateY(-3px);
      box-shadow: var(--shadow-glow);
    }

    .gallery-thumb-container {
      position: relative;
      width: 100%;
      height: 220px;
      background: #020610;
      overflow: hidden;
      cursor: pointer;
    }

    .gallery-thumb-container img {
      width: 100%;
      height: 100%;
      object-fit: cover;
      object-position: center top;
      transition: transform 0.4s ease;
    }

    .gallery-thumb-container:hover img {
      transform: scale(1.05);
    }

    .gallery-overlay {
      position: absolute;
      inset: 0;
      background: rgba(2, 11, 24, 0.6);
      display: flex;
      align-items: center;
      justify-content: center;
      opacity: 0;
      transition: var(--transition);
      color: var(--cyan);
      font-weight: 600;
      font-size: 0.85rem;
      gap: 0.5rem;
    }

    .gallery-thumb-container:hover .gallery-overlay {
      opacity: 1;
    }

    .gallery-body {
      padding: 1.25rem;
      flex: 1;
      display: flex;
      flex-direction: column;
      justify-content: space-between;
    }

    .gallery-title {
      font-size: 0.95rem;
      font-weight: 700;
      color: var(--text-primary);
      margin-bottom: 0.35rem;
    }

    .gallery-desc {
      font-size: 0.82rem;
      color: var(--text-secondary);
      line-height: 1.5;
      margin-bottom: 0.75rem;
    }

    .gallery-tag {
      font-size: 0.7rem;
      color: var(--sky);
      font-family: 'JetBrains Mono', monospace;
    }

    /* Lightbox Modal */
    .lightbox-modal {
      position: fixed;
      inset: 0;
      background: rgba(2, 6, 16, 0.92);
      backdrop-filter: blur(12px);
      z-index: 2000;
      display: none;
      align-items: center;
      justify-content: center;
      padding: 2rem;
    }

    .lightbox-modal.active {
      display: flex;
      animation: modalFade 0.25s ease;
    }

    @keyframes modalFade {
      from { opacity: 0; }
      to { opacity: 1; }
    }

    .lightbox-content {
      max-width: 90vw;
      max-height: 90vh;
      display: flex;
      flex-direction: column;
      align-items: center;
      position: relative;
    }

    .lightbox-img {
      max-width: 100%;
      max-height: 80vh;
      object-fit: contain;
      border-radius: var(--radius-md);
      box-shadow: 0 0 35px rgba(0, 0, 0, 0.8);
      border: 1px solid var(--border-medium);
    }

    .lightbox-caption {
      margin-top: 1rem;
      color: var(--text-primary);
      font-size: 1rem;
      font-weight: 600;
      text-align: center;
      background: var(--bg-card);
      padding: 0.5rem 1.25rem;
      border-radius: var(--radius-full);
      border: 1px solid var(--border-subtle);
    }

    .lightbox-close {
      position: absolute;
      top: -45px;
      right: 0;
      background: var(--bg-card);
      border: 1px solid var(--border-subtle);
      color: var(--text-primary);
      width: 36px;
      height: 36px;
      border-radius: var(--radius-full);
      cursor: pointer;
      display: flex;
      align-items: center;
      justify-content: center;
      transition: var(--transition);
    }

    .lightbox-close:hover {
      color: var(--red);
      border-color: var(--red);
      transform: scale(1.1);
    }

    /* Back to Top */
    .back-to-top {
      position: fixed;
      bottom: 2rem;
      right: 2rem;
      width: 44px;
      height: 44px;
      border-radius: var(--radius-full);
      background: var(--bg-card);
      border: 1px solid var(--border-medium);
      color: var(--cyan);
      display: flex;
      align-items: center;
      justify-content: center;
      cursor: pointer;
      box-shadow: var(--shadow-md);
      opacity: 0;
      pointer-events: none;
      transition: var(--transition);
      z-index: 800;
    }

    .back-to-top.visible {
      opacity: 1;
      pointer-events: auto;
    }

    .back-to-top:hover {
      background: var(--cyan);
      color: #020B18;
      box-shadow: var(--shadow-glow);
      transform: translateY(-3px);
    }

    /* Footer */
    footer {
      border-top: 1px solid var(--border-subtle);
      background: var(--bg-surface);
      padding: 2.5rem 2rem;
      text-align: center;
      margin-top: auto;
      font-size: 0.85rem;
      color: var(--text-muted);
    }

    footer a {
      color: var(--cyan);
      text-decoration: none;
    }

    footer a:hover {
      text-decoration: underline;
    }

    /* Responsive */
    @media (max-width: 1024px) {
      .comparison-grid {
        grid-template-columns: 1fr;
      }
      .main-content {
        padding: 2rem;
        max-width: 100%;
      }
      .sidebar {
        position: fixed;
        left: -100%;
        top: var(--header-height);
        height: calc(100vh - var(--header-height));
        transition: left 0.3s ease;
        box-shadow: 10px 0 30px rgba(0, 0, 0, 0.5);
      }
      .sidebar.open {
        left: 0;
      }
      .mobile-menu-btn {
        display: flex;
      }
    }

    @media (max-width: 768px) {
      .top-header {
        padding: 0 1rem;
      }
      .hero-title {
        font-size: 1.75rem;
      }
      .hero-banner {
        padding: 1.5rem;
      }
      .gallery-grid {
        grid-template-columns: 1fr;
      }
    }
  </style>
</head>
<body>

  <!-- Reading Progress Bar -->
  <div id="progress-bar"></div>

  <!-- Top Header Navigation -->
  <header class="top-header">
    <div class="brand-group">
      <button class="btn-icon mobile-menu-btn" id="mobileMenuToggle" aria-label="Mở menu mục lục">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><line x1="3" y1="12" x2="21" y2="12"></line><line x1="3" y1="6" x2="21" y2="6"></line><line x1="3" y1="18" x2="21" y2="18"></line></svg>
      </button>
      <div class="brand-logo">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M19 17h2c.6 0 1-.4 1-1v-3c0-.9-.7-1.7-1.5-1.9C18.7 10.6 16 10 16 10s-1.3-1.4-2.2-2.3c-.5-.4-1.1-.7-1.8-.7H5c-.6 0-1.1.4-1.4.9l-1.4 2.9A3.7 3.7 0 0 0 2 12v4c0 .6.4 1 1 1h2"/><circle cx="7" cy="17" r="2"/><path d="M9 17h6"/><circle cx="17" cy="17" r="2"/></svg>
      </div>
      <div class="brand-info">
        <h1>NYC TAXI PLATFORM INTELLIGENCE</h1>
        <p>Cẩm Nang Kiến Trúc & Báo Cáo Khảo Sát Toàn Diện 2 Dự Án</p>
      </div>
    </div>

    <div class="header-actions">
      <span class="badge-pill badge-cyan">Lakehouse Batch</span>
      <span class="badge-pill badge-yellow">Real-Time Stream</span>
      <button class="btn-icon" id="themeToggle" title="Chuyển đổi giao diện Sáng / Tối">
        <svg id="themeIcon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="5"/><line x1="12" y1="1" x2="12" y2="3"/><line x1="12" y1="21" x2="12" y2="23"/><line x1="4.22" y1="4.22" x2="5.64" y2="5.64"/><line x1="18.36" y1="18.36" x2="19.78" y2="19.78"/><line x1="1" y1="12" x2="3" y2="12"/><line x1="21" y1="12" x2="23" y2="12"/><line x1="4.22" y1="19.78" x2="5.64" y2="18.36"/><line x1="18.36" y1="5.64" x2="19.78" y2="4.22"/></svg>
      </button>
      <button class="btn-icon" id="printDoc" title="In hoặc lưu dạng PDF">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polyline points="6 9 6 2 18 2 18 9"></polyline><path d="M6 18H4a2 2 0 0 1-2-2v-5a2 2 0 0 1 2-2h16a2 2 0 0 1 2 2v5a2 2 0 0 1-2 2h-2"></path><rect x="6" y="14" width="12" height="8"></rect></svg>
      </button>
    </div>
  </header>

  <!-- App Layout Container -->
  <div class="app-layout">
    
    <!-- Left Navigation Bookmark Sidebar -->
    <aside class="sidebar" id="sidebar">
      <div class="sidebar-header">
        <span class="sidebar-title">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><path d="M19 21l-7-5-7 5V5a2 2 0 0 1 2-2h10a2 2 0 0 1 2 2z"></path></svg>
          Mục Lục Bookmark
        </span>
        <span class="badge-pill badge-cyan" id="navCount">7 Mục</span>
      </div>

      <!-- Instant Filter Search -->
      <div class="search-box">
        <svg class="search-icon" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line></svg>
        <input type="text" class="search-input" id="searchBookmarks" placeholder="Lọc nhanh mục lục..." autocomplete="off">
      </div>

      <!-- Navigation Tree Items -->
      <nav class="nav-sections" id="navMenu">
        
        <!-- Nhóm 1 -->
        <div class="nav-group">
          <div class="nav-group-title">
            <span>I. Tổng Quan Hệ Thống</span>
          </div>
          <ul class="nav-list">
            <li class="nav-item">
              <a href="#sec-overview" class="active">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
                1. Bức Tranh Toàn Cảnh & So Sánh
              </a>
            </li>
          </ul>
        </div>

        <!-- Nhóm 2 -->
        <div class="nav-group">
          <div class="nav-group-title">
            <span>II. Dự Án 1: Taxi Lakehouse</span>
          </div>
          <ul class="nav-list">
            <li class="nav-item">
              <a href="#sec-lakehouse">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>
                2. Kiến Trúc Medallion Pipeline
              </a>
            </li>
            <li class="nav-item">
              <a href="#sec-ylc-report">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
                3. Báo Cáo Phân Tích Yellow Taxi
              </a>
            </li>
            <li class="nav-item">
              <a href="#sec-fhv-report">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
                4. Báo Cáo Dữ Liệu FHV / FHVHV
              </a>
            </li>
          </ul>
        </div>

        <!-- Nhóm 3 -->
        <div class="nav-group">
          <div class="nav-group-title">
            <span>III. Dự Án 2: Taxi Streaming</span>
          </div>
          <ul class="nav-list">
            <li class="nav-item">
              <a href="#sec-streaming">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
                5. Kiến Trúc Real-Time Streaming
              </a>
            </li>
            <li class="nav-item">
              <a href="#sec-data-contract">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
                6. Data Discovery & Canonical Contracts
              </a>
            </li>
          </ul>
        </div>

        <!-- Nhóm 4 -->
        <div class="nav-group">
          <div class="nav-group-title">
            <span>IV. Vận Hành & Triển Khai</span>
          </div>
          <ul class="nav-list">
            <li class="nav-item">
              <a href="#sec-operations">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
                7. Runbooks, Cổng Dịch Vụ & SQL
              </a>
            </li>
          </ul>
        </div>

      </nav>
    </aside>

    <!-- Main Content Area -->
    <main class="main-content">
      
      <!-- HERO BANNER -->
      <section class="hero-banner">
        <div class="hero-tag">
          <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:16px;height:16px;"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          KIẾN TRÚC DỮ LIỆU ĐÔ THỊ NEW YORK CITY
        </div>
        <h1 class="hero-title">Hệ Thống Phân Tích & Giám Sát Dữ Liệu Taxi Toàn Diện</h1>
        <p class="hero-desc">
          Tài liệu hợp nhất mô tả chi tiết 2 nền tảng kỹ thuật dữ liệu độc lập nhưng tương hỗ lẫn nhau: 
          <strong>Data Lakehouse</strong> xử lý phân tích lịch sử quy mô 280+ triệu chuyến đi kết hợp Machine Learning dự báo thời tiết, 
          và <strong>Real-Time Streaming Pipeline</strong> mô phỏng, xử lý luồng sự kiện 400+ eps và trực quan hóa 3D hơn 500 phương tiện trên 265 Taxi Zones New York.
        </p>

        <!-- Metric Cards Grid -->
        <div class="hero-metrics">
          <div class="metric-card metric-cyan">
            <div class="metric-value">279.2M+</div>
            <div class="metric-label">Bản Ghi Lịch Sử Đã Xử Lý</div>
            <div class="metric-sub">35.6M Yellow + 243.6M FHVHV (2025)</div>
          </div>
          <div class="metric-card metric-yellow">
            <div class="metric-value">400+ eps</div>
            <div class="metric-label">Thông Lượng Luồng Thời Gian Thực</div>
            <div class="metric-sub">Kafka KRaft 6 Partitions & Flink 60s</div>
          </div>
          <div class="metric-card metric-purple">
            <div class="metric-value">265 Zones</div>
            <div class="metric-label">Phân Vùng Đô Thị NYC</div>
            <div class="metric-sub">Manhattan, Brooklyn, Queens, Bronx, SI</div>
          </div>
          <div class="metric-card metric-green">
            <div class="metric-value">&lt; 1 Giây</div>
            <div class="metric-label">Độ Trễ End-to-End Live</div>
            <div class="metric-sub">Từ Raw Parquet đến Deck.gl 3D SPA</div>
          </div>
        </div>
      </section>

      <!-- ====================================================================
           PHẦN 1: TỔNG QUAN & SO SÁNH HAI DỰ ÁN
           ==================================================================== -->
      <section id="sec-overview" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="16" x2="12" y2="12"></line><line x1="12" y1="8" x2="12.01" y2="8"></line></svg>
          </div>
          <h2>1. Bức Tranh Toàn Cảnh & So Sánh Đối Chiếu Hai Dự Án</h2>
        </div>

        <div id="sub-synergy">
          <h3 class="subsection-header">1.1 Sứ Mệnh & Mối Quan Hệ Tương Hỗ (Architecture Synergy)</h3>
          <p>
            Trong kỹ thuật dữ liệu hiện đại cho đô thị thông minh (Smart City Data Engineering), không một kiến trúc đơn lẻ nào có thể giải quyết trọn vẹn cả hai yêu cầu: 
            <strong>phân tích dữ liệu lớn lịch sử nhiều năm (Deep OLAP Analytics / ML Training)</strong> và 
            <strong>điều hành phản ứng tức thời theo từng mili-giây (Operational Mission Control / Real-Time Dispatching)</strong>.
          </p>
          <p>
            Không gian làm việc này hiện thực hóa mô hình chuẩn mực <strong>Kiến Trúc Kép (Dual-Engine Platform)</strong> kết hợp giữa hai dự án:
          </p>
          
          <div class="comparison-grid">
            
            <!-- Card Dự Án 1 -->
            <div class="project-card">
              <div class="project-card-header">
                <div class="project-badge-title">
                  <span class="badge-pill badge-cyan">DỰ ÁN 1</span>
                  <h3>NYC Taxi Lakehouse Pipeline</h3>
                </div>
                <span class="tech-tag">Batch & OLAP</span>
              </div>
              <p>
                Xây dựng Data Lakehouse cục bộ theo chuẩn <strong>Medallion Architecture (Bronze &rarr; Silver &rarr; Gold)</strong>. Nạp và chuẩn hóa dữ liệu Parquet khổng lồ từ NYC TLC CDN (Yellow, Green, FHV, FHVHV) kết hợp dữ liệu khí tượng Open-Meteo để huấn luyện mô hình Machine Learning LightGBM dự báo nhu cầu di chuyển và doanh thu 24h tới.
              </p>
              <div>
                <strong style="display:block;margin-bottom:0.4rem;font-size:0.8rem;color:var(--text-muted);text-transform:uppercase;">Công nghệ cốt lõi:</strong>
                <div class="tech-tags">
                  <span class="tech-tag">Apache Spark 3.5</span>
                  <span class="tech-tag">Delta Lake 3.2</span>
                  <span class="tech-tag">MinIO S3</span>
                  <span class="tech-tag">Apache Airflow 2.10</span>
                  <span class="tech-tag">Trino SQL 465</span>
                  <span class="tech-tag">LightGBM</span>
                  <span class="tech-tag">PostgreSQL 16</span>
                </div>
              </div>
              <div class="callout callout-info" style="margin:0;padding:0.75rem 1rem;">
                <div class="callout-title" style="margin-bottom:0.25rem;">Thước đo năng lực:</div>
                <p style="margin:0;font-size:0.85rem;">Xử lý trọn vẹn hơn <strong>279 triệu chuyến đi năm 2025</strong> với cơ chế Quarantine tự động và truy vấn phân tán cực nhanh qua Trino.</p>
              </div>
            </div>

            <!-- Card Dự Án 2 -->
            <div class="project-card">
              <div class="project-card-header">
                <div class="project-badge-title">
                  <span class="badge-pill badge-yellow">DỰ ÁN 2</span>
                  <h3>NYC Taxi Real-Time Streaming</h3>
                </div>
                <span class="tech-tag">Streaming & Live 3D</span>
              </div>
              <p>
                Nền tảng kỹ thuật dữ liệu luồng tốc độ cao (400+ events/s) mô phỏng và giám sát trực tiếp hơn 500 phương tiện đang lăn bánh. Áp dụng Flink Sliding Window 60s để nhận diện điểm nóng tắc đường và tranh chấp thị phần giữa các hãng xe, phát sóng WebSocket tới bảng điều khiển WebGL 3D Deck.gl 60 FPS.
              </p>
              <div>
                <strong style="display:block;margin-bottom:0.4rem;font-size:0.8rem;color:var(--text-muted);text-transform:uppercase;">Công nghệ cốt lõi:</strong>
                <div class="tech-tags">
                  <span class="tech-tag">Apache Kafka 3.8 (KRaft)</span>
                  <span class="tech-tag">Python Flink Engine</span>
                  <span class="tech-tag">Redis 7.2 Alpine</span>
                  <span class="tech-tag">FastAPI WebSockets</span>
                  <span class="tech-tag">React 18 + Vite</span>
                  <span class="tech-tag">Deck.gl 9.0 (WebGL 3D)</span>
                  <span class="tech-tag">Apache ECharts 5.5</span>
                </div>
              </div>
              <div class="callout callout-warning" style="margin:0;padding:0.75rem 1rem;">
                <div class="callout-title" style="margin-bottom:0.25rem;">Thước đo năng lực:</div>
                <p style="margin:0;font-size:0.85rem;">Xử lý <strong>400+ sự kiện mỗi giây</strong>, độ trễ truyền dữ liệu dưới 10ms, trực quan hóa 3D 60 FPS mượt mà không nghẽn luồng.</p>
              </div>
            </div>

          </div>
        </div>

        <div id="sub-comparison">
          <h3 class="subsection-header">1.2 Ma Trận So Sánh Kỹ Thuật Trực Diện</h3>
          <p>
            Bảng đối chiếu chi tiết các khía cạnh kiến trúc, lưu trữ, công nghệ xử lý và mục đích nghiệp vụ của 2 dự án:
          </p>

          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Tiêu Chí Kỹ Thuật</th>
                  <th>Dự Án 1: taxi_lakehouse</th>
                  <th>Dự Án 2: taxi_streaming</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Mục tiêu cốt lõi</strong></td>
                  <td>Lưu trữ dữ liệu lớn dài hạn, làm sạch Medallion, phân tích OLAP và huấn luyện mô hình dự báo ML.</td>
                  <td>Mô phỏng luồng xe di chuyển thực tế, xử lý luồng sự kiện vi mô và hiển thị bảng điều khiển tác chiến 3D.</td>
                </tr>
                <tr>
                  <td><strong>Mô hình dữ liệu</strong></td>
                  <td>Batch Processing (theo tháng / năm, nạp dữ liệu Parquet từ CDN TLC).</td>
                  <td>Stream Processing (sự kiện vi mô: <code>TRIP_STARTED</code>, <code>LOCATION_PING</code>, <code>TRIP_COMPLETED</code>).</td>
                </tr>
                <tr>
                  <td><strong>Quy mô thông lượng</strong></td>
                  <td>279.2M+ dòng dữ liệu lịch sử năm 2025 (~20M bản ghi/tháng).</td>
                  <td>400+ sự kiện/giây (hơn 1.44 triệu sự kiện/giờ phát liên tục).</td>
                </tr>
                <tr>
                  <td><strong>Tầng Lưu trữ & Định dạng</strong></td>
                  <td><strong>MinIO (S3 API) + Delta Lake 3.2</strong> (Parquet + transaction log ACID, Time Travel).</td>
                  <td><strong>Apache Kafka (Topic taxi.trips.live) + Redis 7.2</strong> (Key-Value Snapshots, Pub/Sub channels).</td>
                </tr>
                <tr>
                  <td><strong>Engine Tính toán chính</strong></td>
                  <td><strong>Apache Spark 3.5.3 (PySpark)</strong> xử lý song song phân tán.</td>
                  <td><strong>Python Sliding Window Stream Processor (Flink logic)</strong> cửa sổ trượt 60 giây.</td>
                </tr>
                <tr>
                  <td><strong>Điều phối & Lập lịch</strong></td>
                  <td><strong>Apache Airflow 2.10.3</strong> (DAGs theo chu kỳ tháng và dự báo hàng ngày lúc 00:00 UTC).</td>
                  <td>Vận hành liên tục dạng <strong>Daemons / Event-Driven Microservices</strong> trên Docker Network.</td>
                </tr>
                <tr>
                  <td><strong>Tầng Phục vụ truy vấn</strong></td>
                  <td><strong>Trino 465 SQL Engine</strong> phân tán truy vấn trực tiếp Delta Lake qua MinIO File Metastore.</td>
                  <td><strong>FastAPI ASGI Server</strong> cung cấp REST APIs và WebSockets Broadcast Fan-out.</td>
                </tr>
                <tr>
                  <td><strong>Giao diện người dùng</strong></td>
                  <td>Báo cáo nghiên cứu tĩnh, biểu đồ EDA chuyên sâu Seaborn/Matplotlib và bản đồ tương tác Folium/Leaflet.</td>
                  <td>Ứng dụng Web SPA Single Page (React 18, Vite, Deck.gl 9.0 WebGL 3D 60 FPS, ECharts 5.5 Cyberpunk).</td>
                </tr>
                <tr>
                  <td><strong>Độ trễ xử lý (SLA)</strong></td>
                  <td>Vài phút đến hàng chục phút cho 1 tháng dữ liệu 20 triệu dòng.</td>
                  <td><strong>Dưới 1 giây</strong> từ lúc sinh sự kiện đến khi hiển thị vị trí xe trên bản đồ 3D.</td>
                </tr>
                <tr>
                  <td><strong>Tính năng nâng cao</strong></td>
                  <td>Cơ chế kiểm định Quality Gate + bảng Quarantine, Feature Store thời tiết, suy luận LightGBM 24h.</td>
                  <td>Nội suy định tuyến OSRM bám mạng lưới đường phố NYC, thuật toán phát hiện điểm nóng & phân định thị phần Power Map.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 2: DỰ ÁN 1: NYC TAXI LAKEHOUSE PIPELINE
           ==================================================================== -->
      <section id="sec-lakehouse" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M4 15s1-1 4-1 5 2 8 2 4-1 4-1V3s-1 1-4 1-5-2-8-2-4 1-4 1z"></path><line x1="4" y1="22" x2="4" y2="15"></line></svg>
          </div>
          <h2>2. Dự Án 1: NYC Taxi Lakehouse Pipeline (Medallion Architecture)</h2>
        </div>

        <div id="sub-lakehouse-layers">
          <h3 class="subsection-header">2.1 Kiến Trúc Dữ Liệu Medallion (Bronze &rarr; Silver &rarr; Gold)</h3>
          <p>
            Hệ thống tuân thủ nghiêm ngặt nguyên lý thiết kế Data Lakehouse hiện đại, phân tách hoàn toàn giữa tầng lưu trữ đối tượng (Object Storage - MinIO) và tầng tính toán (Compute - Spark & Trino). 
            Định dạng bảng <strong>Delta Lake 3.2.0</strong> mang lại khả năng thực thi giao dịch ACID, schema enforcement, time-travel và tối ưu hóa ghi đồng thời.
          </p>

          <div class="code-container">
            <div class="code-header">
              <span>Sơ Đồ Luồng Dữ Liệu Medallion Lakehouse</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code>========================================================================================
                             NGUỒN DỮ LIỆU ĐẦU VÀO (EXTERNAL SOURCES)
  + NYC TLC CloudFront CDN (Yellow, Green, FHV, FHVHV định dạng Parquet)
  + Open-Meteo Historical & Forecast Weather API (New York City Coordinates)
========================================================================================
                                           |
                    +----------------------+----------------------+
                    |                                             |
            [Airflow Pipeline]                            [Airflow Pipeline]
           taxi_monthly_pipeline                     taxi_weather_forecast_pipeline
                    |                                             |
                    v                                             v
========================================================================================
                         STORAGE LAYER: MinIO S3-Compatible Buckets
========================================================================================
  [1] s3a://bronze/
      +-- yellow_trips/      Dữ liệu Parquet thô từ TLC + metadata (_ingest_timestamp, _source_file).
      +-- green_trips/
      +-- fhv_trips/
      +-- fhvhv_trips/
      +-- quarantine/        Bản ghi vi phạm Quality Gate (tọa độ lỗi, ngày âm, giá âm...) + _quarantine_reason.

  [2] s3a://silver/
      +-- yellow_trips/      Dữ liệu làm sạch, tính chỉ số dẫn xuất (duration_min, speed_mph, tip_rate),
      +-- green_trips/       phân vùng theo source_month. Định dạng Delta Lake.
      +-- fhvhv_trips/
      +-- dim_taxi_zones/    Bảng thứ nguyên 265 phân vùng taxi NYC (LocationID, Borough, Zone).
      +-- dim_weather_hourly/Dữ liệu thời tiết theo giờ: nhiệt độ, lượng mưa, tuyết, tốc độ gió.

  [3] s3a://gold/
      +-- hourly_zone_metrics/          Tổng hợp số chuyến, doanh thu, tips theo Giờ x Vùng.
      +-- green_hourly_zone_metrics/    Tổng hợp cho dòng taxi xanh.
      +-- fhv_hourly_zone_metrics/      Tổng hợp cho dòng xe công nghệ FHV/FHVHV.
      +-- weather_taxi_features_hourly/ Feature store kết hợp đặc trưng thời gian, lag và thời tiết.
      +-- forecast_hourly_metrics/      Kết quả suy luận 24h từ mô hình LightGBM hồi quy.
========================================================================================
                                 SERVING & AUDIT LAYER
========================================================================================
  + Trino Distributed SQL Engine:
    Truy vấn trực tiếp Delta Lake (delta.bronze, delta.silver, delta.gold) qua MinIO File Metastore.
  + PostgreSQL Audit Store:
    Ghi nhật ký chi tiết pipeline_execution_history (rows_read, rows_written, quarantine_rate, SLA).
========================================================================================</code></pre>
          </div>
        </div>

        <div id="sub-lakehouse-tech">
          <h3 class="subsection-header">2.2 Ngăn Xếp Công Nghệ & Vai Trò Kỹ Thuật</h3>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Thành phần</th>
                  <th>Công nghệ & Phiên bản</th>
                  <th>Vai trò trong Kiến trúc Lakehouse</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Distributed Storage</strong></td>
                  <td><code>MinIO RELEASE.2024+</code></td>
                  <td>Hệ thống lưu trữ đối tượng tương thích chuẩn S3 API, quản lý 3 bucket độc lập: <code>bronze</code>, <code>silver</code>, <code>gold</code>.</td>
                </tr>
                <tr>
                  <td><strong>Table Format</strong></td>
                  <td><code>Delta Lake 3.2.0</code></td>
                  <td>Định dạng bảng ACID cho phép quản lý phiên bản (Time Travel), Schema Enforcement, Partition Pruning và Data Skipping.</td>
                </tr>
                <tr>
                  <td><strong>Compute Engine</strong></td>
                  <td><code>Apache Spark 3.5.3 (PySpark)</code></td>
                  <td>Engine xử lý song song chịu trách nhiệm nạp dữ liệu, áp dụng bộ lọc Quality Gates và tổng hợp số liệu tầng Gold.</td>
                </tr>
                <tr>
                  <td><strong>Workflow Orchestration</strong></td>
                  <td><code>Apache Airflow 2.10.3</code></td>
                  <td>Lập lịch và điều phối các tác vụ ETL theo chuỗi phụ thuộc, tự động kích hoạt suy luận dự báo hàng ngày.</td>
                </tr>
                <tr>
                  <td><strong>Distributed SQL</strong></td>
                  <td><code>Trino 465</code></td>
                  <td>Truy vấn phân tán siêu tốc không cần Hive Metastore cồng kềnh, phân tích trực tiếp trên Delta Lake.</td>
                </tr>
                <tr>
                  <td><strong>Audit Repository</strong></td>
                  <td><code>PostgreSQL 16</code></td>
                  <td>Lưu trữ Airflow Metadata và bảng theo dõi lịch sử vận hành <code>pipeline_execution_history</code>.</td>
                </tr>
                <tr>
                  <td><strong>Machine Learning</strong></td>
                  <td><code>LightGBM 4.x + Scikit-Learn</code></td>
                  <td>Huấn luyện mô hình hồi quy Gradient Boosting dự báo nhu cầu di chuyển và doanh thu theo thời tiết.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div id="sub-lakehouse-dags">
          <h3 class="subsection-header">2.3 Cơ Chế Điều Phối Airflow DAGs & Bộ Lọc Quarantine</h3>
          <p>
            Hệ thống triển khai 2 Airflow DAGs sản xuất với khả năng tham số hóa linh hoạt:
          </p>
          <ul style="padding-left:1.5rem;margin-bottom:1rem;color:var(--text-secondary);">
            <li style="margin-bottom:0.5rem;">
              <strong>DAG 1: <code>taxi_monthly_pipeline</code></strong>: Chạy theo chuỗi 4 giai đoạn <code>bronze_layer &rarr; silver_layer &rarr; gold_layer &rarr; audit_layer</code>. 
              Hỗ trợ trigger với config: loại xe (<code>dataset_type: yellow/green/fhv/fhvhv</code>), dải tháng (<code>source_month: "2025-01..2025-12"</code>), và cơ chế nạp <code>source_mode: REMOTE_NYC_CDN</code> (stream trực tiếp từ CDN vào S3 mà không tốn dung lượng đĩa host).
            </li>
            <li>
              <strong>DAG 2: <code>taxi_weather_forecast_pipeline</code></strong>: Lập lịch chạy tự động lúc <strong>00:00 UTC</strong> mỗi ngày (<code>0 0 * * *</code>). Gồm 3 tác vụ: <code>refresh_weather_forecast &rarr; generate_24h_forecast &rarr; register_and_flush_trino</code>.
            </li>
          </ul>

          <div class="callout callout-warning">
            <div class="callout-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><path d="M10.29 3.86L1.82 18a2 2 0 0 0 1.71 3h16.94a2 2 0 0 0 1.71-3L13.71 3.86a2 2 0 0 0-3.42 0z"></path><line x1="12" y1="9" x2="12" y2="13"></line><line x1="12" y1="17" x2="12.01" y2="17"></line></svg>
              Cơ chế Quality Gate & Xử Lý Bản Ghi Cách Ly (Quarantine Engine)
            </div>
            <p style="margin-bottom:0.5rem;font-size:0.9rem;">
              Bất kỳ bản ghi nào vi phạm các quy tắc tính hợp lý sau sẽ bị chuyển vào bảng <code>s3a://bronze/quarantine</code> kèm mã lỗi chi tiết:
            </p>
            <ul style="padding-left:1.5rem;font-size:0.85rem;color:var(--text-secondary);">
              <li><code>INVALID_DATETIME</code>: Thời gian trả khách diễn ra trước thời gian đón khách (<code>dropoff &le; pickup</code>).</li>
              <li><code>INVALID_DISTANCE</code>: Cự ly bằng 0 hoặc âm, hoặc vượt ngưỡng vô lý (> 1,000 dặm).</li>
              <li><code>INVALID_FARE</code>: Tổng tiền hoặc cước cơ bản âm mà không có cờ tranh chấp hợp lệ.</li>
              <li><code>ORPHAN_ZONE</code>: Mã phân vùng đón/trả khách nằm ngoài danh mục 265 Taxi Zones chuẩn NYC TLC.</li>
            </ul>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 3: BÁO CÁO KHẢO SÁT CHUYÊN SÂU YELLOW TAXI (YLC_REPORT)
           ==================================================================== -->
      <section id="sec-ylc-report" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="12 2 15.09 8.26 22 9.27 17 14.14 18.18 21.02 12 17.77 5.82 21.02 7 14.14 2 9.27 8.91 8.26 12 2"></polygon></svg>
          </div>
          <h2>3. Khảo Sát & Báo Cáo Chuyên Sâu Dữ Liệu Yellow Taxi (YLC_report)</h2>
        </div>

        <div id="sub-ylc-eda">
          <h3 class="subsection-header">3.1 Quy Mô & Chỉ Số Điều Hành Cả Năm 2025</h3>
          <p>
            Báo cáo tổng hợp từ bảng <code>delta.silver.yellow_trips</code> qua Trino SQL Engine trên toàn bộ 366 ngày năm 2025:
          </p>

          <!-- 4 Mini Metric Cards -->
          <div class="hero-metrics" style="margin-bottom:1.5rem;">
            <div class="metric-card metric-yellow">
              <div class="metric-value">35,611,613</div>
              <div class="metric-label">Tổng Số Chuyến Đi Sạch</div>
              <div class="metric-sub">Bao phủ 262 Taxi Zones</div>
            </div>
            <div class="metric-card metric-green">
              <div class="metric-value">$1.051 Tỷ</div>
              <div class="metric-label">Tổng Doanh Thu Hóa Đơn</div>
              <div class="metric-sub">$1,051,466,606.39 USD</div>
            </div>
            <div class="metric-card metric-cyan">
              <div class="metric-value">85.9%</div>
              <div class="metric-label">Thanh Toán Bằng Thẻ</div>
              <div class="metric-sub">Tip in-app minh bạch qua POS</div>
            </div>
            <div class="metric-card metric-purple">
              <div class="metric-value">13.5 Phút</div>
              <div class="metric-label">Thời Lượng Trung Vị (Median)</div>
              <div class="metric-sub">Cự ly trung vị: 1.72 dặm (~2.77 km)</div>
            </div>
          </div>

          <!-- Master Dashboard Image Card -->
          <div class="gallery-card" style="margin-bottom:2rem;">
            <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/01_overview_and_eda/silver_visual_dashboard.png', 'Dashboard Tổng Quan Phân Tích 6-trong-1 Yellow Taxi 2025')">
              <img src="../taxi_lakehouse/report/YLC_report/01_overview_and_eda/silver_visual_dashboard.png" alt="Silver Visual Dashboard Yellow Taxi" loading="lazy">
              <div class="gallery-overlay">
                <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:20px;height:20px;"><circle cx="11" cy="11" r="8"></circle><line x1="21" y1="21" x2="16.65" y2="16.65"></line><line x1="11" y1="8" x2="11" y2="14"></line><line x1="8" y1="11" x2="14" y2="11"></line></svg>
                Nhấp để xem kích thước đầy đủ
              </div>
            </div>
            <div class="gallery-body">
              <div class="gallery-title">Dashboard Tổng Quan Khám Phá Dữ Liệu (Executive EDA 6-trong-1)</div>
              <div class="gallery-desc">
                Trực quan hóa đa chiều: phân bổ thời gian di chuyển, cự ly chuyến đi, ma trận phương thức thanh toán (Thẻ tín dụng 85.9% vs Tiền mặt 13.8%), và tương quan giữa thời điểm gọi xe với doanh thu.
              </div>
              <div class="gallery-tag">File: report/YLC_report/01_overview_and_eda/silver_visual_dashboard.png</div>
            </div>
          </div>
        </div>

        <div id="sub-ylc-dist">
          <h3 class="subsection-header">3.2 Khám Phá Phân Phối Đơn Biến (Histograms & Hiện Tượng Đa Đỉnh)</h3>
          <p>
            Phân tích hình thái phân phối xác suất mang lại những phát hiện tâm lý học và cơ chế giá đặc thù của New York City:
          </p>

          <div class="gallery-grid">
            
            <!-- Tip percentage card -->
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/02_distributions_histograms/03_hist_tip_percentage.png', 'Phân phối tỷ lệ tiền tip trên thẻ tín dụng - 4 đỉnh nhọn sắc nét')">
                <img src="../taxi_lakehouse/report/YLC_report/02_distributions_histograms/03_hist_tip_percentage.png" alt="Tip Percentage Histogram" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Hiện Tượng 4 Đỉnh Nhọn Tiền Tip (Quadrimodal Spikes)</div>
                <div class="gallery-desc">
                  Xuất hiện 4 đỉnh sắc nét tại đúng các mốc: <strong>15%</strong>, <strong>20% (Đỉnh cao nhất)</strong>, <strong>25%</strong>, và <strong>30%</strong>. Chứng minh hành vi khách hàng hoàn toàn bị chi phối bởi các nút bấm gợi ý lập trình sẵn trên máy POS taxi.
                </div>
                <div class="gallery-tag">Tip TB: 25.48% trên các chuyến quẹt thẻ</div>
              </div>
            </div>

            <!-- JFK Flat Rate card -->
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/02_distributions_histograms/04_hist_fare_amount.png', 'Phân phối giá cước cơ bản - Cột đỉnh cô lập $70 JFK Flat Rate')">
                <img src="../taxi_lakehouse/report/YLC_report/02_distributions_histograms/04_hist_fare_amount.png" alt="Fare Amount Histogram" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Bằng Chứng Định Lượng Về Cước Cố Định JFK ($70 Flat Rate)</div>
                <div class="gallery-desc">
                  Ngoài phân phối cước nội đô lệch phải có trung vị $13.48, đồ thị xuất hiện một cột nhọn đứng cô lập tại đúng mức <strong>$70.00</strong> - minh chứng định lượng về quy định cước trọn gói của NYC giữa Manhattan và sân bay JFK.
                </div>
                <div class="gallery-tag">Median: $13.48 | Mean: $19.75</div>
              </div>
            </div>

            <!-- Rush hours bimodal card -->
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/02_distributions_histograms/06_bimodal_rush_hours.png', 'Phân phối 2 đỉnh giờ cao điểm trong ngày')">
                <img src="../taxi_lakehouse/report/YLC_report/02_distributions_histograms/06_bimodal_rush_hours.png" alt="Bimodal Rush Hours" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Phân Phối 2 Đỉnh Khung Giờ Cao Điểm (Bimodal Rush Hours)</div>
                <div class="gallery-desc">
                  Đỉnh sáng lúc <strong>08h-09h (~1.51M chuyến)</strong> phản ánh luồng công sở. Đỉnh chiều tối lúc <strong>17h-19h đạt đỉnh tuyệt đối (~2.56M chuyến)</strong>. Trũng đêm 02h-05h nhu cầu thấp nhất nhưng cước bình quân lại cao nhất ($34-$39) do đi liên quận hoặc ra sân bay.
                </div>
                <div class="gallery-tag">Đỉnh tối gấp 15.4 lần trũng đêm</div>
              </div>
            </div>

            <!-- Trip Distance card -->
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/02_distributions_histograms/02_hist_trip_distance.png', 'Phân phối cự ly di chuyển - Nhóm nội đô & gờ phụ sân bay')">
                <img src="../taxi_lakehouse/report/YLC_report/02_distributions_histograms/02_hist_trip_distance.png" alt="Trip Distance Histogram" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Cự Ly Chuyến Đi & Gờ Phụ Sân Bay (Airport Shoulder)</div>
                <div class="gallery-desc">
                  Hơn 70% chuyến đi là cự ly ngắn nội đô (0.5 - 3.5 dặm). Đồ thị hình thành một "gờ phụ" rõ nét ở dải <strong>12.0 - 18.0 dặm</strong>, tương ứng với khoảng cách thực tế từ Manhattan đi sân bay LaGuardia (~10 mi) và JFK (~16 mi).
                </div>
                <div class="gallery-tag">Trung vị: 1.72 dặm | P90: 14.72 dặm</div>
              </div>
            </div>

          </div>
        </div>

        <div id="sub-ylc-scatter">
          <h3 class="subsection-header">3.3 Tương Quan Đa Biến & Vận Tốc Theo Khung Giờ (Scatter Plots)</h3>
          <div class="gallery-grid">
            
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/03_relationships_scatter/01_scatter_distance_vs_fare.png', 'Tương quan Cự ly vs Giá cước - Đường dốc tuyến tính và đường ngang JFK')">
                <img src="../taxi_lakehouse/report/YLC_report/03_relationships_scatter/01_scatter_distance_vs_fare.png" alt="Distance vs Fare Scatter" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Cự Ly vs Giá Cước: Tương Quan Tuyến Tính & Flat Rate</div>
                <div class="gallery-desc">
                  Tương quan cực mạnh ($r > 0.92$) với công thức: $\text{Fare} \approx \$3.00 + \$3.50 \times \text{Distance}$. Dải điểm nằm ngang cố định tại <strong>$70.00</strong> thể hiện toàn bộ các chuyến đi JFK bất kể cự ly dao động từ 10 đến 25 dặm.
                </div>
                <div class="gallery-tag">Pearson Correlation: r = 0.94</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/03_relationships_scatter/04_scatter_hour_vs_speed.png', 'Khung giờ trong ngày vs Vận tốc di chuyển - 5 Traffic Regimes')">
                <img src="../taxi_lakehouse/report/YLC_report/03_relationships_scatter/04_scatter_hour_vs_speed.png" alt="Hour vs Speed Scatter" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">5 Chế Độ Giao Thông Đô Thị (Traffic Regimes)</div>
                <div class="gallery-desc">
                  Tốc độ di chuyển giảm dốc từ 06h sáng và chạm đáy kẹt xe nội đô lúc <strong>16h - 19h (chỉ đạt ~7.8 - 9.5 mph)</strong>. Vận tốc thông thoáng > 20 mph chỉ tái lập sau 23h đêm đến 05h sáng hôm sau.
                </div>
                <div class="gallery-tag">Đêm rạng sáng: 18 - 25 mph | Giờ tan tầm: &lt; 9 mph</div>
              </div>
            </div>

          </div>
        </div>

        <div id="sub-ylc-heatmaps">
          <h3 class="subsection-header">3.4 Ma Trận Nhiệt Thời Gian & Tương Quan (Heatmaps Analytics)</h3>
          <div class="gallery-grid">
            
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/04_matrix_heatmaps/01_heatmap_weekly_demand.png', 'Nhu cầu theo Thứ trong tuần x Khung giờ trong ngày')">
                <img src="../taxi_lakehouse/report/YLC_report/04_matrix_heatmaps/01_heatmap_weekly_demand.png" alt="Weekly Demand Heatmap" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Ma Trận Nhu Cầu Tuần (Thứ x Giờ Trong Ngày)</div>
                <div class="gallery-desc">
                  Ngày thường (Thứ 2 - Thứ 6) dồn vào giờ tan tầm 17:00 - 19:00 (>400k chuyến/giờ). Cuối tuần chuyển dịch sang <strong>đêm muộn Thứ 6 và Thứ 7 (21:00 - 02:00 sáng)</strong> do hoạt động vui chơi giải trí nightlife.
                </div>
                <div class="gallery-tag">Peak: Thứ 5 & Thứ 6 lúc 18h</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/04_matrix_heatmaps/02_heatmap_weekly_speed.png', 'Bản đồ ùn tắc giao thông tuần - Vận tốc trung bình mph')">
                <img src="../taxi_lakehouse/report/YLC_report/04_matrix_heatmaps/02_heatmap_weekly_speed.png" alt="Weekly Speed Heatmap" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Bản Đồ Ùn Tắc Giao Thông Tuần (Speed Gridlock)</div>
                <div class="gallery-desc">
                  Điểm nghẽn nghiêm trọng nhất toàn thành phố rơi vào chiều <strong>Thứ Năm và Thứ Sáu từ 16:00 đến 19:00</strong> khi vận tốc trung bình chạm đáy <strong>7.8 - 8.3 mph</strong>. Toàn bộ ngày Chủ Nhật lưu thông thông suốt nhất tuần.
                </div>
                <div class="gallery-tag">Đỏ rực: Vùng kẹt xe &lt; 9 mph</div>
              </div>
            </div>

          </div>
        </div>

        <div id="sub-ylc-gis">
          <h3 class="subsection-header">3.5 Phân Tích Địa Lý Không Gian & Mất Cân Bằng Cung - Cầu Xe</h3>
          <p>
            Phân tích GIS trên 262 Taxi Zones cho thấy mạng lưới taxi vàng mang tính tập trung cao độ tại Manhattan:
          </p>

          <div class="gallery-grid">
            
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/05_spatial_gis_analytics/01_spatial_borough_od_heatmap.png', 'Ma trận luồng di chuyển giữa các quận - 83.5% nội quận Manhattan')">
                <img src="../taxi_lakehouse/report/YLC_report/05_spatial_gis_analytics/01_spatial_borough_od_heatmap.png" alt="Borough OD Heatmap" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Ma Trận Di Chuyển Liên Quận: 83.5% Nội Đô Manhattan</div>
                <div class="gallery-desc">
                  Có tới <strong>29.74 triệu chuyến (83.5%)</strong> diễn ra hoàn toàn bên trong Manhattan. Luồng liên quận lớn duy nhất là giữa Manhattan và 2 sân bay JFK/LGA thuộc Queens (>3.7 triệu chuyến).
                </div>
                <div class="gallery-tag">Manhattan &rarr; Manhattan: 29.74M chuyến</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/05_spatial_gis_analytics/02_spatial_zone_netflow_heatmap.png', 'Bản đồ mất cân bằng Cung - Cầu xe - Thâm hụt kỷ lục tại JFK')">
                <img src="../taxi_lakehouse/report/YLC_report/05_spatial_gis_analytics/02_spatial_zone_netflow_heatmap.png" alt="Zone Netflow Heatmap" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Mất Cân Bằng Cung Cầu: Thâm Hụt -1.12 Triệu Xe Tại JFK</div>
                <div class="gallery-desc">
                  Sân bay JFK thâm hụt nặng nhất thành phố: $\text{Net Flow} = \mathbf{-1,120,500}$ xe (khách đón xe rời sân bay nhiều hơn lượt trả). Ngược lại, Upper East Side North dư thừa $\mathbf{+280,400}$ xe do người dân đi taxi về nhà ngủ nhưng sáng đi làm bằng tàu điện ngầm.
                </div>
                <div class="gallery-tag">Thâm hụt cực đại: Sân bay JFK</div>
              </div>
            </div>

          </div>

          <div class="callout callout-info">
            <div class="callout-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>
              Bản Đồ Web Tương Tác Trực Quan Folium / Leaflet Đã Xuất Sẵn
            </div>
            <p style="font-size:0.9rem;margin-bottom:0.75rem;">
              Dự án đã tích hợp sẵn tệp bản đồ tương tác hiển thị vệt nhiệt đón khách, vòng tròn đỏ (Deficit) và xanh lá (Surplus) kèm popup thông tin đầy đủ cho từng phân vùng:
            </p>
            <a href="../taxi_lakehouse/report/YLC_report/05_spatial_gis_analytics/interactive_spatial_heatmap.html" target="_blank" class="badge-pill badge-cyan" style="font-size:0.85rem;padding:0.4rem 0.8rem;text-decoration:none;">
              Mở Bản Đồ Tương Tác YLC (Leaflet HTML) &rarr;
            </a>
          </div>
        </div>

        <div id="sub-ylc-weather">
          <h3 class="subsection-header">3.6 Tác Động Của Thời Tiết & Mô Hình Machine Learning LightGBM</h3>
          <p>
            Khảo sát trên toàn bộ <strong>8,759 giờ</strong> năm 2025 tại New York City kết hợp dữ liệu khí tượng Open-Meteo và huấn luyện mô hình LightGBM dự báo nhu cầu & doanh thu:
          </p>

          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Trạng Thái Thời Tiết</th>
                  <th>Số Giờ Xuất Hiện</th>
                  <th>Nhu Cầu TB / Giờ</th>
                  <th>Doanh Thu TB / Giờ</th>
                  <th>Giá Cước TB / Chuyến</th>
                  <th>Lượng Mưa TB</th>
                  <th>Nhiệt Độ TB</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Clear (Trời quang)</strong></td>
                  <td>2,843 giờ</td>
                  <td>3,755.6 chuyến</td>
                  <td>$110,948.76</td>
                  <td>$29.54</td>
                  <td>0.0 mm</td>
                  <td>12.30°C</td>
                </tr>
                <tr>
                  <td><strong>Cloudy (Nhiều mây)</strong></td>
                  <td>4,707 giờ</td>
                  <td>4,152.5 chuyến</td>
                  <td>$122,586.29</td>
                  <td>$29.52</td>
                  <td>0.0 mm</td>
                  <td>12.31°C</td>
                </tr>
                <tr>
                  <td><strong>Drizzle (Mưa phùn)</strong></td>
                  <td>845 giờ</td>
                  <td><strong>4,635.4 chuyến</strong></td>
                  <td><strong>$136,907.25</strong></td>
                  <td>$29.54</td>
                  <td>0.36 mm</td>
                  <td>16.05°C</td>
                </tr>
                <tr>
                  <td><strong>Rain (Mưa rào)</strong></td>
                  <td>229 giờ</td>
                  <td>4,349.9 chuyến</td>
                  <td>$129,244.93</td>
                  <td><strong>$29.71</strong></td>
                  <td>3.21 mm</td>
                  <td>15.71°C</td>
                </tr>
                <tr>
                  <td><strong>Snow (Tuyết rơi)</strong></td>
                  <td>135 giờ</td>
                  <td>3,524.0 chuyến</td>
                  <td>$96,831.10</td>
                  <td>$27.48</td>
                  <td>0.58 mm</td>
                  <td>-1.34°C</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="gallery-grid">
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/06_weather_forecast_models/forecast_24h_dashboard.png', 'Dashboard dự báo nhu cầu & doanh thu 24h đối soát với thời tiết thực tế')">
                <img src="../taxi_lakehouse/report/YLC_report/06_weather_forecast_models/forecast_24h_dashboard.png" alt="24h Forecast Dashboard" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Dashboard Suy Luận Dự Báo 24h (LightGBM Regression)</div>
                <div class="gallery-desc">
                  Mô hình LightGBM kết hợp các đặc trưng chuỗi thời gian (Hour, DayOfWeek), đặc trưng trễ (Lag 24h, 168h) và các biến thời tiết (Nhiệt độ, Mưa, Gió) để suy luận nhu cầu và doanh thu cho 24 giờ tiếp theo.
                </div>
                <div class="gallery-tag">MAE &lt; 8.5% so với thực tế</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/YLC_report/06_weather_forecast_models/weather_condition_impact.png', 'Tác động của trạng thái thời tiết tới nhu cầu và cước phí taxi')">
                <img src="../taxi_lakehouse/report/YLC_report/06_weather_forecast_models/weather_condition_impact.png" alt="Weather Condition Impact" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Tác Động Của Mưa & Nhiệt Độ Cực Đoan</div>
                <div class="gallery-desc">
                  Mưa phùn (Drizzle) kích thích nhu cầu tăng <strong>+23.4%</strong> so với trời trong xanh do người dân hạn chế đi bộ. Nhiệt độ nắng gắt (>30°C) ghi nhận mức cước và nhu cầu trung bình giờ cao kỷ lục ($164,178/giờ).
                </div>
                <div class="gallery-tag">Nhiệt độ &gt; 30°C: 5,471 chuyến/giờ</div>
              </div>
            </div>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 4: BÁO CÁO DỮ LIỆU FHV / FHVHV (UBER & LYFT)
           ==================================================================== -->
      <section id="sec-fhv-report" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="1" y="3" width="15" height="13"></rect><polygon points="16 8 20 8 23 11 23 16 16 16 8"></polygon><circle cx="5.5" cy="18.5" r="2.5"></circle><circle cx="18.5" cy="18.5" r="2.5"></circle></svg>
          </div>
          <h2>4. Khảo Sát & Đánh Giá Dữ Liệu FHV / FHVHV (Uber & Lyft Lakehouse)</h2>
        </div>

        <div id="sub-fhv-audit">
          <h3 class="subsection-header">4.1 Báo Cáo Kiểm Định Chất Lượng Dữ Liệu Tầng Silver (FHV_DATA.md)</h3>
          <p>
            Đợt kiểm toán chất lượng toàn diện trên tập dữ liệu xe công nghệ công suất cao <code>delta.silver.fhvhv_trips</code>:
          </p>

          <div class="hero-metrics" style="margin-bottom:1.5rem;">
            <div class="metric-card metric-purple">
              <div class="metric-value">243.58M</div>
              <div class="metric-label">Tổng Dòng Bronze Raw</div>
              <div class="metric-sub">12 tháng trọn vẹn năm 2025</div>
            </div>
            <div class="metric-card metric-green">
              <div class="metric-value">99.9947%</div>
              <div class="metric-label">Tỷ Lệ Chuyển Đổi Thành Công</div>
              <div class="metric-sub">243,576,832 dòng vào Silver</div>
            </div>
            <div class="metric-card metric-yellow">
              <div class="metric-value">12,204</div>
              <div class="metric-label">Số Dòng Bị Cách Ly Quarantine</div>
              <div class="metric-sub">100% do hiện tượng lùi giờ DST</div>
            </div>
            <div class="metric-card metric-cyan">
              <div class="metric-value">0 Orphan</div>
              <div class="metric-label">Toàn Vẹn Khóa Ngoại Zones</div>
              <div class="metric-sub">Khớp 100% với dim_taxi_zones</div>
            </div>
          </div>

          <div class="gallery-card" style="margin-bottom:2rem;">
            <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/FHV_report/01_overview_and_eda/silver_visual_dashboard.png', 'Dashboard Tổng Quan Phân Tích Dữ Liệu FHVHV 243.5 Triệu Chuyến Đi')">
              <img src="../taxi_lakehouse/report/FHV_report/01_overview_and_eda/silver_visual_dashboard.png" alt="Silver Visual Dashboard FHVHV" loading="lazy">
              <div class="gallery-overlay">Nhấp để xem kích thước đầy đủ</div>
            </div>
            <div class="gallery-body">
              <div class="gallery-title">Executive Dashboard Khảo Sát FHVHV (Uber & Lyft) Toàn Năm 2025</div>
              <div class="gallery-desc">
                Quy mô khổng lồ gấp gần 7 lần Yellow Taxi (~20 triệu chuyến/tháng). Cự ly trung vị đạt <strong>2.76 dặm</strong> (cao hơn đáng kể so với 1.72 dặm của taxi vàng) và thời lượng trung vị là <strong>16.0 phút</strong>.
              </div>
              <div class="gallery-tag">File: report/FHV_report/01_overview_and_eda/silver_visual_dashboard.png</div>
            </div>
          </div>
        </div>

        <div id="sub-fhv-matrix">
          <h3 class="subsection-header">4.2 Ma Trận Đầy Đủ Dữ Liệu 28 Cột & Sự Cố Lùi Giờ DST</h3>
          <p>
            Dữ liệu Silver FHVHV bao gồm 28 trường được chuẩn hóa và phân vùng theo <code>pickup_month</code> và <code>pickup_date</code>:
          </p>

          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Nhóm Trường</th>
                  <th>Tên Cột Chính</th>
                  <th>Kiểu Dữ Liệu</th>
                  <th>Tỷ Lệ NULL</th>
                  <th>Ghi Chú Kỹ Thuật & Nghiệp Vụ</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Mốc thời gian</strong></td>
                  <td><code>tpep_pickup_datetime</code>, <code>tpep_dropoff_datetime</code></td>
                  <td><code>timestamp(3) with tz</code></td>
                  <td><span class="badge-pill badge-green">0.00%</span></td>
                  <td>Bao phủ trọn vẹn 365 ngày từ 01/01/2025 đến 31/12/2025.</td>
                </tr>
                <tr>
                  <td><strong>Phân vùng địa lý</strong></td>
                  <td><code>pu_location_id</code>, <code>do_location_id</code></td>
                  <td><code>integer</code></td>
                  <td><span class="badge-pill badge-green">0.00%</span></td>
                  <td>Khớp chính xác với danh mục 265 Taxi Zones, không có khóa mồ côi.</td>
                </tr>
                <tr>
                  <td><strong>Chỉ số tài chính</strong></td>
                  <td><code>trip_distance</code>, <code>fare_amount</code>, <code>total_amount</code>, <code>tip_amount</code></td>
                  <td><code>double</code> / <code>decimal</code></td>
                  <td><span class="badge-pill badge-green">0.00%</span></td>
                  <td>Cự ly TB 5.03 mi, Cước cơ bản TB $26.95, Tổng cước TB $33.36, Tip TB $1.19.</td>
                </tr>
                <tr>
                  <td><strong>Mã nhà cung cấp</strong></td>
                  <td><code>vendor_id</code></td>
                  <td><code>integer</code></td>
                  <td><span class="badge-pill badge-green">0.00%</span></td>
                  <td>Mã hóa: <strong>Uber = 3</strong> (175.98M chuyến - 72.2%), <strong>Lyft = 5</strong> (67.60M chuyến - 27.8%).</td>
                </tr>
                <tr>
                  <td><strong>Metadata hệ thống</strong></td>
                  <td><code>_ingested_at</code>, <code>_batch_id</code>, <code>_transformed_at</code></td>
                  <td><code>timestamp</code> / <code>varchar</code></td>
                  <td><span class="badge-pill badge-green">0.00%</span></td>
                  <td>Đảm bảo khả năng truy vết nguồn gốc (Data Lineage) 100%.</td>
                </tr>
                <tr>
                  <td><strong>Trường không áp dụng</strong></td>
                  <td><code>passenger_count</code>, <code>rate_code_id</code>, <code>store_and_fwd_flag</code>, <code>payment_type</code></td>
                  <td><code>integer</code> / <code>varchar</code></td>
                  <td><span class="badge-pill badge-yellow">100.0%</span></td>
                  <td>Hợp lệ về nghiệp vụ: Ứng dụng Uber/Lyft thanh toán 100% in-app và không ghi số khách hoặc cờ taximeter.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <div class="callout callout-warning">
            <div class="callout-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><circle cx="12" cy="12" r="10"></circle><line x1="12" y1="8" x2="12" y2="12"></line><line x1="12" y1="16" x2="12.01" y2="16"></line></svg>
              Giải mã 12,204 bản ghi bị đưa vào Quarantine (Sự cố DST tháng 11/2025)
            </div>
            <p style="font-size:0.88rem;margin:0;">
              Kiểm tra chi tiết cho thấy toàn bộ 100% các dòng bị cách ly đều thuộc về tháng 11/2025 (<code>fhvhv_tripdata_2025-11</code>). 
              Nguyên nhân do hiện tượng <strong>Daylight Saving Time (DST) Fall-Back</strong> vào rạng sáng 02/11/2025: đồng hồ địa phương tại New York bị lùi 1 tiếng từ 02:00 về 01:00. Dữ liệu ghi nhận mốc kết thúc chuyến trước mốc bắt đầu tính theo giờ địa phương, kích hoạt quy tắc cách ly an toàn của Quality Gate.
            </p>
          </div>
        </div>

        <div id="sub-fhv-market">
          <h3 class="subsection-header">4.3 Phân Tích Thị Phần & Định Giá Cước: Uber (72.2%) vs Lyft (27.8%)</h3>
          <p>
            Tập dữ liệu FHVHV ghi nhận <strong>175,980,947 chuyến Uber</strong> (mã <code>vendor_id = 3</code> / HV0003) và <strong>67,596,502 chuyến Lyft</strong> (mã <code>vendor_id = 5</code> / HV0005). 
            Khảo sát tương quan giá cước và cự ly cho thấy mô hình tính cước động (Surge Pricing / Prime Time) rất rõ rệt:
          </p>

          <div class="gallery-grid">
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/FHV_report/03_relationships_scatter/01_scatter_distance_vs_fare.png', 'So sánh tương quan Cự ly vs Giá cước giữa Uber và Lyft')">
                <img src="../taxi_lakehouse/report/FHV_report/03_relationships_scatter/01_scatter_distance_vs_fare.png" alt="FHV Distance vs Fare Uber vs Lyft" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Định Giá Cước: Uber vs Lyft Trên Cùng Quãng Đường</div>
                <div class="gallery-desc">
                  Giá cước cơ bản trung bình đạt <strong>$26.95</strong>, tổng tiền trung bình <strong>$33.36</strong>. Đồ thị phân tán thể hiện các cụm định giá động đa tầng theo mật độ giao thông và thời gian thực.
                </div>
                <div class="gallery-tag">Uber: 72.2% thị phần | Lyft: 27.8% thị phần</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/FHV_report/04_matrix_heatmaps/03_heatmap_feature_correlation.png', 'Ma trận tương quan Pearson giữa cước phí, cự ly và thu nhập tài xế Driver Pay')">
                <img src="../taxi_lakehouse/report/FHV_report/04_matrix_heatmaps/03_heatmap_feature_correlation.png" alt="FHV Feature Correlation" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Ma Trận Tương Quan: Cước Khách Trả vs Driver Pay</div>
                <div class="gallery-desc">
                  Tương quan giữa cước khách trả (<code>base_passenger_fare</code>) và thu nhập thực nhận của tài xế (<code>driver_pay</code>) đạt $r = 0.89$, phản ánh tỷ lệ trích khấu hao hoa hồng nền tảng app ổn định ~20 - 25%.
                </div>
                <div class="gallery-tag">Driver Pay TB: $20.45/chuyến</div>
              </div>
            </div>
          </div>
        </div>

        <div id="sub-fhv-gis">
          <h3 class="subsection-header">4.4 Mạng Lưới Phủ Sóng 5 Quận & Mỏ Vàng Kinh Tế Sân Bay</h3>
          <p>
            Trực quan hóa không gian thể hiện sự tương phản sâu sắc giữa Yellow Taxi và xe công nghệ FHVHV:
          </p>

          <div class="gallery-grid">
            
            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/FHV_report/05_spatial_gis_analytics/01_spatial_borough_od_heatmap.png', 'Ma trận luồng di chuyển 5 quận FHVHV - Phủ sóng mạnh mẽ Brooklyn, Queens, Bronx')">
                <img src="../taxi_lakehouse/report/FHV_report/05_spatial_gis_analytics/01_spatial_borough_od_heatmap.png" alt="FHV Borough OD Heatmap" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Độ Bao Phủ 5 Quận: Sức Mạnh Ngoại Thành Của Uber & Lyft</div>
                <div class="gallery-desc">
                  Trong khi taxi vàng co cụm 83.5% ở Manhattan, Uber & Lyft phục vụ sâu rộng tại các quận ngoại thành: <strong>Brooklyn &rarr; Brooklyn (~4.23M chuyến/tháng)</strong>, <strong>Queens &rarr; Queens (~2.81M)</strong>, và <strong>Bronx &rarr; Bronx (~1.91M)</strong>.
                </div>
                <div class="gallery-tag">Brooklyn nội quận chiếm tỷ trọng khổng lồ</div>
              </div>
            </div>

            <div class="gallery-card">
              <div class="gallery-thumb-container" onclick="openLightbox('../taxi_lakehouse/report/FHV_report/05_spatial_gis_analytics/03_spatial_zone_revenue_heatmap.png', 'Mỏ vàng kinh tế đa chỉ số FHVHV - Sân bay JFK $24.09M/tháng')">
                <img src="../taxi_lakehouse/report/FHV_report/05_spatial_gis_analytics/03_spatial_zone_revenue_heatmap.png" alt="FHV Zone Revenue Multi Metric" loading="lazy">
                <div class="gallery-overlay">Xem ảnh phóng to</div>
              </div>
              <div class="gallery-body">
                <div class="gallery-title">Mỏ Vàng Kinh Tế: Sân Bay JFK & LGA Đạt Doanh Thu $43M+/tháng</div>
                <div class="gallery-desc">
                  Sân bay JFK dẫn đầu tuyệt đối với <strong>$24.09M doanh thu cước/tháng</strong>, cước bình quân <strong>$65.77/chuyến</strong>, cự ly 18.35 dặm và thu nhập tài xế đạt <strong>$54.38/chuyến</strong>. Sân bay LaGuardia đóng góp thêm $19.16M/tháng.
                </div>
                <div class="gallery-tag">JFK Cước TB: $65.77 | Driver Pay: $54.38</div>
              </div>
            </div>

          </div>

          <div class="callout callout-info">
            <div class="callout-title">
              <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:18px;height:18px;"><polygon points="3 11 22 2 13 21 11 13 3 11"></polygon></svg>
              Bản Đồ Web Tương Tác Trực Quan FHV Leaflet
            </div>
            <p style="font-size:0.9rem;margin-bottom:0.75rem;">
              Khảo sát các điểm thâm hụt nặng (East Village Net Flow -40.3k, Times Square -38.6k) và dư thừa (Crown Heights North +16.9k) trên bản đồ tương tác:
            </p>
            <a href="../taxi_lakehouse/report/FHV_report/05_spatial_gis_analytics/interactive_spatial_heatmap.html" target="_blank" class="badge-pill badge-purple" style="font-size:0.85rem;padding:0.4rem 0.8rem;text-decoration:none;">
              Mở Bản Đồ Tương Tác FHVHV (Leaflet HTML) &rarr;
            </a>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 5: DỰ ÁN 2: NYC TAXI REAL-TIME STREAMING PIPELINE
           ==================================================================== -->
      <section id="sec-streaming" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><polygon points="13 2 3 14 12 14 11 22 21 10 12 10 13 2"></polygon></svg>
          </div>
          <h2>5. Dự Án 2: NYC Taxi Real-Time Streaming Pipeline</h2>
        </div>

        <div id="sub-streaming-6tier">
          <h3 class="subsection-header">5.1 Kiến Trúc 6 Tầng Microservices Vận Hành Độc Lập</h3>
          <p>
            Hệ thống streaming được thiết kế theo mô hình 6 microservices vận hành trên mạng nội bộ Docker Network, cam kết luồng dữ liệu liên tục từ tệp tin Parquet raw đến giao diện WebGL 3D với độ trễ dưới 1 giây:
          </p>

          <div class="code-container">
            <div class="code-header">
              <span>Sơ Đồ Luồng Dữ Liệu Thời Gian Thực 6 Tầng</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code>========================================================================================
                          KIẾN TRÚC LUỒNG DỮ LIỆU THỜI GIAN THỰC (6 TẦNG)
========================================================================================

  +-----------------------+       +-----------------------+       +-----------------------+
  |      SIMULATOR        |       |     APACHE KAFKA      |       |    FLINK PROCESSOR    |
  |  (Parquet Replay &    |------>|  (KRaft Mode, Topic   |------>| (Sliding Window 60s,  |
  |   OSRM Interpolation, |       |   taxi.trips.live,    |       |  Congestion Engine,   |
  |   400+ events/giây)   |       |   6 Partitions, Gzip) |       |  Dominance Analysis)  |
  +-----------------------+       +-----------------------+       +-----------------------+
                                                                              |
                                                                              | Snapshot Sink
                                                                              v
  +-----------------------+       +-----------------------+       +-----------------------+
  |     WEB DASHBOARD     |       |      API GATEWAY      |       |       REDIS 7.2       |
  | (React 18 + Deck.gl 3D|<------| (FastAPI + WebSockets |<------|  (In-Memory State &   |
  |  ECharts 60 FPS SPA)  |  WSS  |  Fan-out Engine,      | Cache |   Pub/Sub Store,      |
  |                       |       |  OSRM Routing Proxy)  | Poll  |   KPI Atomic Counter) |
  +-----------------------+       +-----------------------+       +-----------------------+
========================================================================================</code></pre>
          </div>
        </div>

        <div id="sub-streaming-simulator">
          <h3 class="subsection-header">5.2 Tầng 1 & 2: Simulator (400+ eps) & Message Broker (Apache Kafka KRaft)</h3>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Hạng Mục Kỹ Thuật</th>
                  <th>Đặc Tả Chi Tiết</th>
                  <th>Ý Nghĩa Vận Hành</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Tỷ trọng 3 dòng xe</strong></td>
                  <td>Yellow Cab: <strong>40%</strong> | Green Boro: <strong>10%</strong> | FHVHV (Uber/Lyft): <strong>50%</strong></td>
                  <td>Tái lập đúng tỷ lệ thị phần thực tế trên đường phố New York.</td>
                </tr>
                <tr>
                  <td><strong>2 Chế độ phát dữ liệu</strong></td>
                  <td><code>PARQUET_REPLAY</code> (đọc tệp Parquet TLC) và <code>SYNTHETIC_STREAM</code> (sinh theo trọng số vùng).</td>
                  <td>Linh hoạt giữa kiểm thử tải tổng hợp và mô phỏng chính xác từ lịch sử.</td>
                </tr>
                <tr>
                  <td><strong>Producer Async Kép</strong></td>
                  <td><code>asyncio.Queue</code> (buffer 4,000) + <code>AIOKafkaProducer</code> (batch 100 sự kiện).</td>
                  <td>Đảm bảo thông lượng phát <strong>400+ sự kiện/giây</strong> mà không gây lag CPU.</td>
                </tr>
                <tr>
                  <td><strong>Vòng đời sự kiện</strong></td>
                  <td><code>TRIP_STARTED</code> (0.0) &rarr; <code>LOCATION_PING</code> (0.0 &lt; p &lt; 1.0) &rarr; <code>TRIP_COMPLETED</code> (1.0)</td>
                  <td>Theo dõi tiến độ hành trình và tọa độ di chuyển theo thời gian thực.</td>
                </tr>
                <tr>
                  <td><strong>Kafka KRaft Broker</strong></td>
                  <td>Apache Kafka 3.8.0, <strong>6 Partitions</strong>, nén <code>gzip</code>, retention 1h / 512 MB.</td>
                  <td>Loại bỏ ZooKeeper, tối ưu đọc ghi song song, chống tràn đĩa máy chủ.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div id="sub-streaming-flink">
          <h3 class="subsection-header">5.3 Tầng 3: Engine Xử Lý Luồng (Sliding Window & Power Map)</h3>
          <p>
            Mô-đun <code>flink_processor/</code> thực thi các thuật toán tính toán biên liên tục:
          </p>
          <ul style="padding-left:1.5rem;color:var(--text-secondary);margin-bottom:1rem;">
            <li style="margin-bottom:0.5rem;">
              <strong>Cửa sổ trượt 60 giây (Sliding Window 60s)</strong>: Duy trì vị trí GPS, vận tốc, cước phí hiện tại và tự động thu hồi (Stale Eviction) các xe không còn phát tín hiệu ping hoặc đã hoàn thành cuốc.
            </li>
            <li style="margin-bottom:0.5rem;">
              <strong>Bộ phân loại ùn tắc (Zone Congestion Classifier)</strong>: Đánh giá mật độ trên 265 Taxi Zones theo 4 cấp độ: 
              <code>LOW (&lt;3 xe)</code>, <code>MODERATE (3-6 xe)</code>, <code>HEAVY (7-11 xe)</code>, và <code>CRITICAL (&ge;12 xe)</code>.
            </li>
            <li>
              <strong>Thuật toán bản đồ tranh chấp thị phần (Power Map Dominance)</strong>: Hàm <code>compute_zone_dominance()</code> xác định đội xe chiếm đa số và trạng thái trận địa: 
              <code>DOMINATED</code> (chiếm &ge;50% và cách biệt lớn), <code>CONTESTED</code> (vùng tranh chấp giằng co giữa 2 hãng), hoặc <code>BALANCED</code>.
            </li>
          </ul>
        </div>

        <div id="sub-streaming-gateway">
          <h3 class="subsection-header">5.4 Tầng 4 & 5: Redis State Store & Real-Time API Gateway</h3>
          <p>
            Cấu trúc khóa và cơ chế phân phối dữ liệu hiệu năng cao:
          </p>

          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Redis Key / Channel</th>
                  <th>Kiểu Dữ Liệu</th>
                  <th>TTL Hết Hạn</th>
                  <th>Mục Đích Sử Dụng</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>kv:latest_density_metrics</code></td>
                  <td>String (JSON)</td>
                  <td>Không</td>
                  <td>Snapshot toàn bộ 265 zones, danh sách xe active (tọa độ, vận tốc, tiến trình).</td>
                </tr>
                <tr>
                  <td><code>kv:power_map_snapshot</code></td>
                  <td>String (JSON)</td>
                  <td><strong>10 giây</strong></td>
                  <td>Danh sách zone tranh chấp (invasion zones) và số vùng kiểm soát của từng hãng.</td>
                </tr>
                <tr>
                  <td><code>hash:realtime_kpis</code></td>
                  <td>Hash</td>
                  <td>Không</td>
                  <td>Bộ đếm nguyên tử: <code>total_active_vehicles</code>, <code>total_events_processed</code>.</td>
                </tr>
                <tr>
                  <td><code>channel:density_metrics</code></td>
                  <td>Pub/Sub Channel</td>
                  <td>Không</td>
                  <td>Kênh phát sóng snapshot mỗi 2 giây cho các client WebSocket lắng nghe trực tiếp.</td>
                </tr>
              </tbody>
            </table>
          </div>

          <p>
            <strong>Real-Time API Gateway (FastAPI)</strong>:
            Cung cấp điểm cuối <code>WebSocket /ws/fleet</code> (truyền tọa độ xe cho Deck.gl), <code>WebSocket /ws/kpis</code> (truyền số liệu vận hành cho ECharts), 
            và <code>GET /api/route</code> (Reverse Proxy cho OSRM Routing Engine trả về polyline bám mặt đường phố NYC).
          </p>
        </div>

        <div id="sub-streaming-ui">
          <h3 class="subsection-header">5.5 Tầng 6: Mission Control Web SPA (Deck.gl 3D, ECharts 5.5, Cyberpunk)</h3>
          <p>
            Bảng điều hành tác chiến phân tách thành 3 không gian chuyên biệt:
          </p>

          <div class="tabs-wrapper">
            <div class="tab-nav">
              <button class="tab-btn active" onclick="switchTab(this, 'tab-map')">Tab 1: 3D Fleet Command Map</button>
              <button class="tab-btn" onclick="switchTab(this, 'tab-telemetry')">Tab 2: Live Stream Telemetry</button>
              <button class="tab-btn" onclick="switchTab(this, 'tab-intel')">Tab 3: Deep Intelligence</button>
            </div>

            <!-- Tab 1 -->
            <div id="tab-map" class="tab-pane active">
              <div class="callout callout-info" style="margin-top:0;">
                <div class="callout-title">Bản Đồ Chỉ Huy 3D GPU-Accelerated 60 FPS (Deck.gl 9.0 + MapLibre GL)</div>
                <ul style="padding-left:1.5rem;font-size:0.88rem;color:var(--text-secondary);">
                  <li>Hiển thị đồng thời hơn 500 phương tiện với màu phân định: Vàng (#FACC15 - Yellow), Xanh lá (#22C55E - Green), Tím (#A855F7 - FHVHV).</li>
                  <li>Lớp phủ trực quan: Bản đồ nhiệt nhu cầu (Demand Heatmap), vòng tròn radar phát sóng tại khu vực đông nhất, và 3 sân bay quốc tế (JFK, LGA, EWR).</li>
                  <li>HUD Lái xe tương tác: Nhấp vào xe bất kỳ để camera 3D bay tới, vẽ lộ trình thực tế qua OSRM (nhánh đã qua màu Cyan, nhánh sắp tới màu Crimson) và tính Detour Score.</li>
                </ul>
              </div>
            </div>

            <!-- Tab 2 -->
            <div id="tab-telemetry" class="tab-pane">
              <div class="callout callout-warning" style="margin-top:0;">
                <div class="callout-title">Nhịp Đập Hệ Thống & Đo Xa Tức Thời (Live Stream Telemetry & Trends)</div>
                <ul style="padding-left:1.5rem;font-size:0.88rem;color:var(--text-secondary);">
                  <li>4 Thẻ KPI vận hành thời gian thực: Active Fleet, Ingestion Throughput (events/s), In-Flight Fare Revenue ($), và Fleet Average Speed (MPH).</li>
                  <li>3 Biểu đồ phân tích nhịp tim: Hotspots Bar Chart (Top 8 điểm nóng ùn tắc), Throughput & Velocity Dual-Axis Wave, và Fare Value Distribution Histogram.</li>
                  <li>Micro-Batch Live Trip Feed: Bảng cập nhật sự kiện vi mô với tính năng Click-to-Inspect định vị xe tức thì.</li>
                </ul>
              </div>
            </div>

            <!-- Tab 3 -->
            <div id="tab-intel" class="tab-pane">
              <div class="callout callout-success" style="margin-top:0;">
                <div class="callout-title">Phân Tích Chuyên Sâu Đội Xe (Fleet Analytics & Deep Intelligence)</div>
                <ul style="padding-left:1.5rem;font-size:0.88rem;color:var(--text-secondary);">
                  <li>3-Fleet Scoreboard: So sánh trực diện thị phần, cước trung bình, vận tốc và tỷ lệ hoàn thành chuyến giữa Yellow, Green và FHVHV.</li>
                  <li>Borough Transition Matrix Heatmap: Ma trận nhiệt trực quan hóa luồng dịch chuyển đón - trả khách giữa 5 quận New York.</li>
                  <li>5-Axis Performance Radar: Biểu đồ mạng nhện đánh giá 5 chiều: Vận tốc, Cước bình quân, Độ phủ, Tỷ lệ đón sân bay, và Doanh thu trên mỗi dặm.</li>
                </ul>
              </div>
            </div>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 6: DATA DISCOVERY & CANONICAL DATA CONTRACTS
           ==================================================================== -->
      <section id="sec-data-contract" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z"></path><polyline points="14 2 14 8 20 8"></polyline><line x1="16" y1="13" x2="8" y2="13"></line><line x1="16" y1="17" x2="8" y2="17"></line><polyline points="10 9 9 9 8 9"></polyline></svg>
          </div>
          <h2>6. Khảo Sát Dữ Liệu Nguồn & Hợp Đồng Giao Tiếp (Data Contracts)</h2>
        </div>

        <div id="sub-discovery-parquet">
          <h3 class="subsection-header">6.1 Khảo Sát Tệp Tin Parquet Tháng 04/2026 (DATA_DISCOVERY.md)</h3>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Tập Dữ Liệu Parquet</th>
                  <th>Dung Lượng</th>
                  <th>Số Dòng Thực Tế</th>
                  <th>Số Cột</th>
                  <th>Tỷ Lệ Null Cột Điển Hình</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><code>yellow_tripdata_2026-04.parquet</code></td>
                  <td>61.82 MB</td>
                  <td>3,831,240 dòng</td>
                  <td>20 cột</td>
                  <td><code>passenger_count</code>, <code>RatecodeID</code>, <code>congestion_surcharge</code>: 20.9% NULL.</td>
                </tr>
                <tr>
                  <td><code>green_tripdata_2026-04.parquet</code></td>
                  <td>1.03 MB</td>
                  <td>51,402 dòng</td>
                  <td>20 cột</td>
                  <td><code>ehail_fee</code>: 100.0% NULL. Phục vụ chủ yếu Upper Manhattan và ngoại ô.</td>
                </tr>
                <tr>
                  <td><code>fhvhv_tripdata_2026-04.parquet</code></td>
                  <td>486.25 MB</td>
                  <td>19,534,810 dòng</td>
                  <td>24 cột</td>
                  <td>Đặc thù xe công nghệ: <code>originating_base_num</code>, <code>on_scene_datetime</code>, <code>tips</code>.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div id="sub-discovery-schema">
          <h3 class="subsection-header">6.2 Đặc Tả Schema Sự Kiện Chuẩn Tắc (Canonical Event Schema)</h3>
          <p>
            Mọi thông điệp truyền trên Kafka topic <code>taxi.trips.live</code> đều được chuẩn hóa theo Pydantic Schema:
          </p>

          <div class="code-container">
            <div class="code-header">
              <span>JSON Schema: taxi.trips.live Canonical Message</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code>{
  "trip_id": "yt-202604-000142",
  "dataset_source": "YELLOW",
  "event_type": "LOCATION_PING",
  "pickup_datetime": "2026-04-12T14:30:00",
  "dropoff_datetime": "2026-04-12T14:48:00",
  "PULocationID": 237,
  "DOLocationID": 161,
  "pickup_zone_name": "Upper East Side South",
  "pickup_borough": "Manhattan",
  "dropoff_zone_name": "Midtown Center",
  "dropoff_borough": "Manhattan",
  "current_lat": 40.7682,
  "current_lng": -73.9621,
  "passenger_count": 1,
  "trip_distance": 2.45,
  "total_amount": 16.50,
  "progress_ratio": 0.42,
  "timestamp": 1776004245.12,
  "datetime_utc": "2026-04-12T18:30:45.120000+00:00"
}</code></pre>
          </div>
        </div>

        <div id="sub-discovery-slas">
          <h3 class="subsection-header">6.3 Cam Kết SLAs & Hiệu Năng Kỹ Thuật (DATA_FLOW.md)</h3>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Chỉ Số SLA</th>
                  <th>Mức Cam Kết</th>
                  <th>Cơ Chế Kỹ Thuật Đảm Bảo</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><strong>Thông lượng phát (Simulator)</strong></td>
                  <td>&ge; 400 events/s</td>
                  <td><code>asyncio.Queue</code> (buffer 4000) kết hợp <code>aiokafka</code> batch sending 100 sự kiện.</td>
                </tr>
                <tr>
                  <td><strong>Độ trễ truyền tin Kafka</strong></td>
                  <td>&lt; 5 ms</td>
                  <td>Kafka 3.8.0 KRaft mode chạy trên Docker network nội bộ, 6 partitions.</td>
                </tr>
                <tr>
                  <td><strong>Chu kỳ xử lý Stream (Flink Tick)</strong></td>
                  <td>2.0 giây</td>
                  <td>Sliding Window bộ nhớ 60s + Redis Pipeline Write nguyên tử.</td>
                </tr>
                <tr>
                  <td><strong>Độ trễ phát sóng WebSocket</strong></td>
                  <td>&lt; 20 ms</td>
                  <td>FastAPI Async Event Loop kết hợp Broadcast channels.</td>
                </tr>
                <tr>
                  <td><strong>Tốc độ dựng hình UI (Frame Rate)</strong></td>
                  <td>60 FPS</td>
                  <td>Deck.gl 9.0 WebGL GPU-accelerated rendering.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

      </section>

      <!-- ====================================================================
           PHẦN 7: VẬN HÀNH, TRIỂN KHAI & BẢNG CỔNG
           ==================================================================== -->
      <section id="sec-operations" class="section-block">
        <div class="section-header">
          <div class="section-icon">
            <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2"><rect x="2" y="2" width="20" height="8" rx="2" ry="2"></rect><rect x="2" y="14" width="20" height="8" rx="2" ry="2"></rect><line x1="6" y1="6" x2="6.01" y2="6"></line><line x1="6" y1="18" x2="6.01" y2="18"></line></svg>
          </div>
          <h2>7. Hướng Dẫn Vận Hành, Triển Khai & Bảng Tra Cứu Nhanh</h2>
        </div>

        <div id="sub-ops-ports">
          <h3 class="subsection-header">7.1 Ma Trận Cổng & Điểm Cuối Dịch Vụ Cả 2 Dự Án</h3>
          <div class="table-container">
            <table>
              <thead>
                <tr>
                  <th>Dự Án</th>
                  <th>Dịch Vụ</th>
                  <th>Địa Chỉ URL / Port</th>
                  <th>Xác Thực Mặc Định</th>
                  <th>Chức Năng Chính</th>
                </tr>
              </thead>
              <tbody>
                <tr>
                  <td><span class="badge-pill badge-cyan">Lakehouse</span></td>
                  <td><strong>Airflow Webserver</strong></td>
                  <td><code>http://localhost:8090</code></td>
                  <td>admin / 12345678</td>
                  <td>Điều phối, quản lý và kích hoạt các DAGs ETL / Forecast.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-cyan">Lakehouse</span></td>
                  <td><strong>MinIO Console</strong></td>
                  <td><code>http://localhost:9001</code></td>
                  <td>admin / 12345678</td>
                  <td>Quản lý giao diện Web các buckets: bronze, silver, gold.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-cyan">Lakehouse</span></td>
                  <td><strong>MinIO S3 API</strong></td>
                  <td><code>http://localhost:9000</code></td>
                  <td>Access/Secret key</td>
                  <td>Endpoint kết nối S3A cho Apache Spark và Trino.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-cyan">Lakehouse</span></td>
                  <td><strong>Trino Web UI</strong></td>
                  <td><code>http://localhost:8080</code></td>
                  <td>trino</td>
                  <td>Theo dõi tiến trình và hiệu năng các câu truy vấn phân tán.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-cyan">Lakehouse</span></td>
                  <td><strong>PostgreSQL</strong></td>
                  <td><code>localhost:5432</code></td>
                  <td>airflow / airflow</td>
                  <td>Lưu Airflow Metadata & bảng kiểm toán <code>pipeline_execution_history</code>.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-yellow">Streaming</span></td>
                  <td><strong>Mission Control SPA</strong></td>
                  <td><code>http://localhost:3000</code></td>
                  <td>Truy cập tự do</td>
                  <td>Bảng điều khiển tác chiến 3D Deck.gl và Telemetry ECharts.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-yellow">Streaming</span></td>
                  <td><strong>FastAPI Gateway</strong></td>
                  <td><code>http://localhost:8080/docs</code></td>
                  <td>Swagger UI</td>
                  <td>Kiểm tra REST APIs và kết nối WebSockets <code>/ws/fleet</code>.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-yellow">Streaming</span></td>
                  <td><strong>Kafka Broker</strong></td>
                  <td><code>localhost:19092</code></td>
                  <td>PLAINTEXT</td>
                  <td>Cổng truy cập ngoài cho topic <code>taxi.trips.live</code>.</td>
                </tr>
                <tr>
                  <td><span class="badge-pill badge-yellow">Streaming</span></td>
                  <td><strong>Redis In-Memory</strong></td>
                  <td><code>localhost:6379</code></td>
                  <td>Không mật khẩu</td>
                  <td>Truy xuất tức thời Key-Value Snapshots & Pub/Sub.</td>
                </tr>
              </tbody>
            </table>
          </div>
        </div>

        <div id="sub-ops-commands">
          <h3 class="subsection-header">7.2 Lệnh Khởi Chạy & Giám Sát Docker Compose</h3>

          <div class="code-container">
            <div class="code-header">
              <span>Bash: Khởi chạy và vận hành taxi_lakehouse</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code># 1. Chuyển vào thư mục Lakehouse
cd /run/media/pch1101/PCH/Build/Data/Taxi/taxi_lakehouse

# 2. Tạo biến môi trường từ mẫu và khởi chạy cụm container
cp .env.example .env
docker compose up -d

# 3. Kiểm tra trạng thái sẵn sàng của các dịch vụ
docker compose ps

# 4. Kích hoạt Airflow DAG qua CLI (Ví dụ: chạy tháng 01/2025 cho xe Yellow)
docker exec -it airflow-webserver airflow dags trigger taxi_monthly_pipeline \
  --conf '{"dataset_type": "yellow", "source_month": "2025-01", "source_mode": "REMOTE_NYC_CDN"}'

# 5. Theo dõi nhật ký kiểm toán trên PostgreSQL
docker exec -it postgres psql -U airflow -d airflow -c "
SELECT id, dag_id, dataset_type, source_month, duration_seconds, bronze_rows, silver_rows, quarantine_rows, gold_rows, status
FROM pipeline_execution_history ORDER BY id DESC LIMIT 5;
"</code></pre>
          </div>

          <div class="code-container">
            <div class="code-header">
              <span>Bash: Khởi chạy và vận hành taxi_streaming</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code># 1. Chuyển vào thư mục Streaming
cd /run/media/pch1101/PCH/Build/Data/Taxi/taxi_streaming

# 2. Khởi chạy toàn bộ cụm 6 microservices
docker compose up -d --build

# 3. Theo dõi trực tiếp logs luồng phát Kafka Simulator
docker compose logs -f simulator

# 4. Kiểm tra snapshot mật độ trên Redis
docker exec -it redis redis-cli get kv:power_map_snapshot

# 5. Chạy thử nghiệm Simulator ở chế độ Dry-Run độc lập (không cần Kafka)
python simulator/main.py --dry-run -n 50</code></pre>
          </div>
        </div>

        <div id="sub-ops-trino">
          <h3 class="subsection-header">7.3 Bộ Truy Vấn Mẫu Đối Soát Trên Trino Phân Tán</h3>

          <div class="code-container">
            <div class="code-header">
              <span>SQL: Đối soát dữ liệu giữa các tầng Medallion qua Trino CLI</span>
              <button class="btn-copy" onclick="copyCode(this)">Sao chép</button>
            </div>
            <pre><code>-- Kết nối Trino CLI: docker exec -it trino trino --catalog delta

-- 1. Đối soát tổng số dòng giữa các tầng Medallion
SELECT '1. Bronze Yellow' AS layer, count(*) AS total_records FROM delta.bronze.yellow_trips
UNION ALL
SELECT '2. Bronze Quarantine', count(*) FROM delta.bronze.quarantine
UNION ALL
SELECT '3. Silver Yellow', count(*) FROM delta.silver.yellow_trips
UNION ALL
SELECT '4. Gold Hourly Metrics', count(*) FROM delta.gold.hourly_zone_metrics
UNION ALL
SELECT '5. Gold 24h Forecast', count(*) FROM delta.gold.forecast_hourly_metrics;

-- 2. Thống kê top 5 nguyên nhân bị cách ly Quarantine
SELECT 
    _quarantine_reason,
    count(*) AS error_count,
    ROUND(count(*) * 100.0 / SUM(count(*)) OVER (), 2) AS percentage
FROM delta.bronze.quarantine
GROUP BY _quarantine_reason
ORDER BY error_count DESC
LIMIT 5;

-- 3. Top 10 Taxi Zones có doanh thu cao nhất (Tầng Gold)
SELECT 
    borough,
    zone_name,
    SUM(trip_count) AS total_trips,
    ROUND(SUM(total_revenue), 2) AS grand_total_revenue,
    ROUND(AVG(tip_rate) * 100, 2) AS avg_tip_percentage
FROM delta.gold.hourly_zone_metrics
GROUP BY borough, zone_name
ORDER BY grand_total_revenue DESC
LIMIT 10;

-- 4. Đọc kết quả dự báo nhu cầu & doanh thu 24h tới kết hợp thời tiết
SELECT 
    forecast_timestamp,
    temp_celsius,
    precipitation_mm,
    predicted_demand_trips,
    predicted_revenue_usd
FROM delta.gold.forecast_hourly_metrics
ORDER BY forecast_timestamp ASC
LIMIT 24;</code></pre>
          </div>
        </div>

      </section>

      <!-- LIGHTBOX MODAL -->
      <div class="lightbox-modal" id="lightboxModal" onclick="closeLightbox(event)">
        <div class="lightbox-content">
          <button class="lightbox-close" onclick="closeLightboxDirect()">&times;</button>
          <img class="lightbox-img" id="lightboxImg" src="" alt="Enlarged Visual">
          <div class="lightbox-caption" id="lightboxCaption"></div>
        </div>
      </div>

      <!-- BACK TO TOP BUTTON -->
      <button class="back-to-top" id="backToTop" title="Lên đầu trang">
        <svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" style="width:20px;height:20px;"><line x1="12" y1="19" x2="12" y2="5"></line><polyline points="5 12 12 5 19 12"></polyline></svg>
      </button>

    </main>
  </div>

  <!-- Footer -->
  <footer>
    <div style="max-width:800px;margin:0 auto;">
      <p style="margin-bottom:0.5rem;font-weight:600;color:var(--text-primary);">
        NYC Taxi Platform Intelligence Documentation &copy; 2026
      </p>
      <p style="font-size:0.8rem;color:var(--text-muted);margin-bottom:0.75rem;">
        Hệ thống phân tích Data Lakehouse & Real-Time Streaming Pipeline cho dữ liệu giao thông đô thị New York City TLC.
      </p>
      <p style="font-size:0.75rem;color:var(--text-muted);">
        Tham khảo mã nguồn: 
        <a href="../taxi_lakehouse/README.md">taxi_lakehouse/README.md</a> &bull; 
        <a href="../taxi_streaming/README.md">taxi_streaming/README.md</a> &bull; 
        <a href="../taxi_streaming/docs/DATA_FLOW.md">docs/DATA_FLOW.md</a> &bull; 
        <a href="../taxi_lakehouse/report/FHV_report/FHV_DATA.md">FHV_DATA.md</a>
      </p>
    </div>
  </footer>

  <!-- SCRIPT: INTERACTION, SEARCH, SCROLLSPY, TABS, LIGHTBOX -->
  <script>
    // 1. Reading Progress Bar
    window.addEventListener('scroll', () => {
      const winScroll = document.documentElement.scrollTop || document.body.scrollTop;
      const height = document.documentElement.scrollHeight - document.documentElement.clientHeight;
      const scrolled = (winScroll / height) * 100;
      document.getElementById('progress-bar').style.width = scrolled + '%';
      
      // Back to top visibility
      const backToTop = document.getElementById('backToTop');
      if (winScroll > 400) {
        backToTop.classList.add('visible');
      } else {
        backToTop.classList.remove('visible');
      }
    });

    document.getElementById('backToTop').addEventListener('click', () => {
      window.scrollTo({ top: 0, behavior: 'smooth' });
    });

    // 2. Theme Toggle (Dark / Light)
    const themeToggle = document.getElementById('themeToggle');
    themeToggle.addEventListener('click', () => {
      const currentTheme = document.documentElement.getAttribute('data-theme');
      const newTheme = currentTheme === 'light' ? 'dark' : 'light';
      document.documentElement.setAttribute('data-theme', newTheme);
      localStorage.setItem('taxi_doc_theme', newTheme);
    });

    // Load saved theme
    const savedTheme = localStorage.getItem('taxi_doc_theme');
    if (savedTheme) {
      document.documentElement.setAttribute('data-theme', savedTheme);
    }

    // 3. Print Doc
    document.getElementById('printDoc').addEventListener('click', () => {
      window.print();
    });

    // 4. Mobile Menu Drawer
    const mobileMenuToggle = document.getElementById('mobileMenuToggle');
    const sidebar = document.getElementById('sidebar');
    mobileMenuToggle.addEventListener('click', () => {
      sidebar.classList.toggle('open');
    });

    // Close sidebar on item click (mobile)
    document.querySelectorAll('.sidebar a').forEach(link => {
      link.addEventListener('click', () => {
        if (window.innerWidth <= 1024) {
          sidebar.classList.remove('open');
        }
      });
    });

    // 5. Instant Bookmark Search & Filter
    const searchBookmarks = document.getElementById('searchBookmarks');
    searchBookmarks.addEventListener('input', (e) => {
      const query = e.target.value.toLowerCase().trim();
      const navItems = document.querySelectorAll('.nav-item');
      let visibleCount = 0;

      navItems.forEach(item => {
        const text = item.textContent.toLowerCase();
        if (text.includes(query)) {
          item.style.display = 'block';
          visibleCount++;
        } else {
          item.style.display = 'none';
        }
      });

      document.getElementById('navCount').textContent = visibleCount + ' Mục';
    });

    // 6. ScrollSpy for Active Links
    const sections = document.querySelectorAll('section[id]');
    const navLinks = document.querySelectorAll('.sidebar .nav-item a');

    window.addEventListener('scroll', () => {
      let currentId = '';
      const scrollPos = window.scrollY + 140;

      sections.forEach(sec => {
        if (sec.offsetTop <= scrollPos) {
          currentId = sec.getAttribute('id');
        }
      });

      if (currentId) {
        navLinks.forEach(link => {
          link.classList.remove('active');
          if (link.getAttribute('href') === '#' + currentId) {
            link.classList.add('active');
          }
        });
      }
    });

    // 7. Tabs Switcher
    function switchTab(btn, targetPaneId) {
      const parentWrapper = btn.closest('.tabs-wrapper');
      parentWrapper.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
      parentWrapper.querySelectorAll('.tab-pane').forEach(p => p.classList.remove('active'));
      
      btn.classList.add('active');
      const targetPane = document.getElementById(targetPaneId);
      if (targetPane) {
        targetPane.classList.add('active');
      }
    }

    // 8. Copy Code Snippet
    function copyCode(btn) {
      const pre = btn.closest('.code-container').querySelector('pre');
      const code = pre.innerText;
      navigator.clipboard.writeText(code).then(() => {
        const originalText = btn.textContent;
        btn.textContent = 'Đã chép!';
        btn.style.color = 'var(--cyan)';
        setTimeout(() => {
          btn.textContent = originalText;
          btn.style.color = '';
        }, 2000);
      });
    }

    // 9. Lightbox Modal
    const lightboxModal = document.getElementById('lightboxModal');
    const lightboxImg = document.getElementById('lightboxImg');
    const lightboxCaption = document.getElementById('lightboxCaption');

    function openLightbox(src, caption) {
      lightboxImg.src = src;
      lightboxCaption.textContent = caption || '';
      lightboxModal.classList.add('active');
      document.body.style.overflow = 'hidden';
    }

    function closeLightbox(e) {
      if (e.target === lightboxModal || e.target.classList.contains('lightbox-close')) {
        closeLightboxDirect();
      }
    }

    function closeLightboxDirect() {
      lightboxModal.classList.remove('active');
      document.body.style.overflow = 'auto';
    }

    document.addEventListener('keydown', (e) => {
      if (e.key === 'Escape' && lightboxModal.classList.contains('active')) {
        closeLightboxDirect();
      }
    });
  </script>
</body>
</html>
"""
    return html_content

def main():
    target_path = "/run/media/pch1101/PCH/Build/Data/Taxi/docs/index.html"
    print(f"Generating HTML documentation at {target_path}...")
    content = generate_html()
    with open(target_path, "w", encoding="utf-8") as f:
        f.write(content)
    print(f"Successfully generated {target_path} ({len(content)} bytes)")

if __name__ == "__main__":
    main()
