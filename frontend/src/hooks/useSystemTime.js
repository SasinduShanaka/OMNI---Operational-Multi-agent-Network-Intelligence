import { useEffect, useState } from 'react'

function formatTime(date) {
  return new Intl.DateTimeFormat('en-US', {
    hour: '2-digit',
    minute: '2-digit',
    second: '2-digit',
    hour12: false,
  }).format(date)
}

export function useSystemTime() {
  const [time, setTime] = useState(() => formatTime(new Date()))

  useEffect(() => {
    const intervalId = setInterval(() => {
      setTime(formatTime(new Date()))
    }, 1000)

    return () => clearInterval(intervalId)
  }, [])

  return time
}
