export function TaskList({ tasks }) {
  return (
    <ul>
      {tasks.map((task) => (
        <li key={task.id}>{task.title.trim()}</li>
      ))}
    </ul>
  )
}