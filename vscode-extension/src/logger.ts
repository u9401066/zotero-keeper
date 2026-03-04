/**
 * Unified Logger for Zotero MCP Extension
 *
 * 集中式日誌管理，所有模組共用同一個 OutputChannel。
 * 支援日誌等級、結構化輸出、開發除錯。
 *
 * Usage:
 *   import { Logger } from './logger';
 *   const log = Logger.getLogger('McpProvider');
 *   log.info('Server started', { servers: 2 });
 *   log.error('Connection failed', { host: '...', err });
 */

import * as vscode from 'vscode';

export enum LogLevel {
    DEBUG = 0,
    INFO = 1,
    WARN = 2,
    ERROR = 3,
}

const LOG_LEVEL_LABELS: Record<LogLevel, string> = {
    [LogLevel.DEBUG]: 'DEBUG',
    [LogLevel.INFO]: 'INFO',
    [LogLevel.WARN]: 'WARN',
    [LogLevel.ERROR]: 'ERROR',
};

/**
 * 具名 Logger 實例，綁定特定模組名稱
 */
export class ComponentLogger {
    constructor(
        private readonly component: string,
        private readonly parent: Logger,
    ) {}

    debug(message: string, data?: Record<string, unknown>): void {
        this.parent.log(LogLevel.DEBUG, this.component, message, data);
    }

    info(message: string, data?: Record<string, unknown>): void {
        this.parent.log(LogLevel.INFO, this.component, message, data);
    }

    warn(message: string, data?: Record<string, unknown>): void {
        this.parent.log(LogLevel.WARN, this.component, message, data);
    }

    error(message: string, data?: Record<string, unknown>): void {
        this.parent.log(LogLevel.ERROR, this.component, message, data);
    }
}

/**
 * 集中式 Logger — 全擴充功能共用一個 OutputChannel
 */
export class Logger {
    private static instance: Logger | undefined;
    private outputChannel: vscode.OutputChannel | undefined;
    private level: LogLevel = LogLevel.INFO;

    private constructor() {}

    static getInstance(): Logger {
        if (!Logger.instance) {
            Logger.instance = new Logger();
        }
        return Logger.instance;
    }

    /**
     * 初始化 Logger（在 extension activate 時呼叫一次）
     */
    init(outputChannel: vscode.OutputChannel, level?: LogLevel): void {
        this.outputChannel = outputChannel;
        if (level !== undefined) {
            this.level = level;
        }
    }

    /**
     * 從設定讀取日誌等級
     */
    setLevelFromConfig(): void {
        const config = vscode.workspace.getConfiguration('zoteroMcp');
        const levelStr = config.get<string>('logLevel', 'info').toUpperCase();
        const mapped: Record<string, LogLevel> = {
            'DEBUG': LogLevel.DEBUG,
            'INFO': LogLevel.INFO,
            'WARN': LogLevel.WARN,
            'ERROR': LogLevel.ERROR,
        };
        this.level = mapped[levelStr] ?? LogLevel.INFO;
    }

    /**
     * 取得具名 Logger（每個模組用自己的名稱）
     */
    static getLogger(component: string): ComponentLogger {
        return new ComponentLogger(component, Logger.getInstance());
    }

    /**
     * 寫入日誌
     */
    log(level: LogLevel, component: string, message: string, data?: Record<string, unknown>): void {
        if (level < this.level) {
            return;
        }

        const timestamp = new Date().toISOString();
        const levelLabel = LOG_LEVEL_LABELS[level];
        const prefix = `[${timestamp}] [${levelLabel}] [${component}]`;

        let line: string;
        if (data && Object.keys(data).length > 0) {
            // 結構化資料：展平為 key=value
            const extra = Object.entries(data)
                .map(([k, v]) => {
                    if (v instanceof Error) {
                        return `${k}=${v.message}`;
                    }
                    if (typeof v === 'string') {
                        return `${k}="${v}"`;
                    }
                    return `${k}=${JSON.stringify(v)}`;
                })
                .join(' ');
            line = `${prefix} ${message} | ${extra}`;
        } else {
            line = `${prefix} ${message}`;
        }

        // 寫入 OutputChannel（使用者可見）
        this.outputChannel?.appendLine(line);

        // 同時寫入 console（開發者工具可見）
        switch (level) {
            case LogLevel.ERROR:
                console.error(line);
                break;
            case LogLevel.WARN:
                console.warn(line);
                break;
            default:
                console.log(line);
                break;
        }
    }

    /**
     * 顯示 Output Channel
     */
    show(): void {
        this.outputChannel?.show();
    }

    /**
     * 釋放資源
     */
    dispose(): void {
        this.outputChannel?.dispose();
        Logger.instance = undefined;
    }
}
