import { BACKEND_URL } from "../config"

export async function checkAuth(): Promise<boolean> {

    const access = localStorage.getItem("access_token")
    const refresh = localStorage.getItem("refresh_token")

    if (!access || !refresh) return false

    try {
        const res = await fetch(`${BACKEND_URL}/auth/refresh`, {
            method: "POST",
            headers: {
                "Content-Type": "application/json"
            },
            body: JSON.stringify({
                refresh_token: refresh
            })
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
        return false
    }
}