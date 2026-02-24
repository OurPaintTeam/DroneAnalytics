import { useEffect, useState } from "react"
import "./App.css"
import {BACKEND_URL} from "./config"

function App() {
    const [message, setMessage] = useState<string>("Загрузка...")

    useEffect(() => {
        fetch(`${BACKEND_URL}`)
            .then((res) => res.json())
            .then((data) => setMessage(data.message))
            .catch(() => setMessage("Ошибка подключения к backend"))
    }, [])

    return (
        <>
            <h1>Frontend + FastPI</h1>
            <p>Сообщение с backend:</p>
            <h2>{message}</h2>
        </>
    )
}

export default App