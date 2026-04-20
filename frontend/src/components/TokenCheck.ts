import {BACKEND_URL} from "../config"
import {ApiError, ApiErrorCode} from "./notify.ts";

async function validateTokenOnServer(token: string): Promise<boolean> {
    try {
        /*  const res = await fetch(`${BACKEND_URL}/auth/validate`, {
              method: "POST",
              headers: {
                  "Content-Type": "application/json",
                  Authorization: `Bearer ${token}`
              }
          })*/
        if (token) {
            return true
        }
        return false
    } catch {
        return false
    }
}

export async function refreshAccessToken(): Promise<boolean> {
    try {
        const res = await fetch(`${BACKEND_URL}/auth/refresh`, {
            method: "POST",
            credentials: "include",
            headers: {
                "Content-Type": "application/json"
            }
        })

        if (!res.ok) {
            localStorage.removeItem("access_token")
            return false
        }

        const data = await res.json()

        if (!data.access_token) {
            localStorage.removeItem("access_token")
            return false
        }

        localStorage.setItem("access_token", data.access_token)
        return true
    } catch {
        localStorage.removeItem("access_token")
        return false
    }
}

export async function checkAuth(): Promise<void> {
    const token = localStorage.getItem("access_token")

    if (!token) {
        throw new ApiError(ApiErrorCode.NO_TOKEN)
    }

    // 1. backend validate
    const isValid = await validateTokenOnServer(token)

    if (isValid) return

    // 2. refresh
    const refreshed = await refreshAccessToken()

    if (!refreshed) {
        throw new ApiError(ApiErrorCode.UNAUTHORIZED)
    }

    // 3. повторная проверка
    const newToken = localStorage.getItem("access_token")

    const isValidAfter = await validateTokenOnServer(newToken!)

    if (isValidAfter) return

    throw new ApiError(ApiErrorCode.UNAUTHORIZED)
}

export function getAccessToken(): string | null {
    return localStorage.getItem("access_token")
}

export async function logout(): Promise<void> {
    const token = localStorage.getItem("access_token")

    try {
        if (token) {
            await fetch(`${BACKEND_URL}/auth/logout`, {
                method: "POST",
                credentials: "include",
                headers: {
                    Authorization: `Bearer ${token}`,
                },
            })
        }
    } catch {
    } finally {
        localStorage.removeItem("access_token")
    }
}