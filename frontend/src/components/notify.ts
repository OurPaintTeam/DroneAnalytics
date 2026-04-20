import { useNotificationStore } from "./notificationStore"
import {logout} from "./TokenCheck.ts";

// @ts-ignore
export enum ApiErrorCode {
    NO_TOKEN = "NO_TOKEN",
    UNAUTHORIZED = "UNAUTHORIZED",
    FORBIDDEN = "FORBIDDEN",
    NOT_FOUND = "NOT_FOUND",
    NETWORK_ERROR = "NETWORK_ERROR",
    BACKEND_DOWN = "BACKEND_DOWN",
    SERVER_ERROR = "SERVER_ERROR",
    INVALID_RESPONSE = "INVALID_RESPONSE"
}

export class ApiError extends Error {
    code: ApiErrorCode

    constructor(code: ApiErrorCode, message?: string) {
        super(message ?? code)
        this.code = code
    }
}

export function handleAuthError(error: unknown, navigate: any) {
    if (error instanceof Error && error.message === "NO_TOKEN") {
        logout()
        navigate("/login", { replace: true })
    }
}

export function handleApiError(error: unknown) {
    if (!(error instanceof ApiError)) {
        notifyError("Неизвестная ошибка")
        return
    }

    const map: Record<ApiErrorCode, string> = {
        NO_TOKEN: "Нет токена — выполните вход",
        UNAUTHORIZED: "Сессия истекла",
        FORBIDDEN: "Нет доступа",
        NOT_FOUND: "Данные не найдены",
        NETWORK_ERROR: "Нет соединения с сервером",
        BACKEND_DOWN: "Backend не отвечает",
        SERVER_ERROR: "Ошибка сервера",
        INVALID_RESPONSE: "Некорректный ответ сервера"
    }

    notifyError(map[error.code] ?? "Ошибка запроса")
}

export function notifyError(message: string) {
    useNotificationStore.getState().add("error", message)
}

export function notifySuccess(message: string) {
    useNotificationStore.getState().add("success", message)
}