export async function fetchTasks() {
  const response = await fetch('/api/tasks')
  if (!response.ok) throw new Error('Unable to load tasks')
  return response.json()
}
