import { BACKEND_URL } from "../config"

export async function checkAuth(): Promise<boolean> {
    const access = localStorage.getItem("access_token")
    if (access) return true

    try {
        const res = await fetch(`${BACKEND_URL}/auth/refresh`, {
            method: "POST",
            credentials: "include"
        })

        if (!res.ok) {
            localStorage.removeItem("access_token")
            localStorage.removeItem("refresh_token")
            return false
        }

        const data = await res.json()
        localStorage.setItem("access_token", data.access_token)
        localStorage.setItem("refresh_token", data.refresh_token)
        return true
    } catch {
        localStorage.removeItem("access_token")
        localStorage.removeItem("refresh_token")
        return false
    }
}
