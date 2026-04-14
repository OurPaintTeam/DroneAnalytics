import { BACKEND_URL } from "../config"

async function validateTokenOnServer(token: string): Promise<boolean> {
    try {
        const res = await fetch(`${BACKEND_URL}/auth/validate`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json",
                Authorization: `Bearer ${token}`
            }
        })

        return res.ok
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

export async function checkAuth(): Promise<boolean> {
    const token = localStorage.getItem("access_token")

    if (!token) {
        return await refreshAccessToken()
    }

    const isValid = await validateTokenOnServer(token)

    if (isValid) {
        return true
    }

    return await refreshAccessToken()
}

export async function logout(): Promise<void> {
    const token = localStorage.getItem("access_token")

    try {
        if (token) {
            await fetch(`${BACKEND_URL}/auth/logout`, {
                method: "POST",
                credentials: "include",
                headers: {
                    Authorization: `Bearer ${token}`
                }
            })
        }
    } catch {
    } finally {
        localStorage.removeItem("access_token")
    }
}

export function getAccessToken(): string | null {
    return localStorage.getItem("access_token")
}