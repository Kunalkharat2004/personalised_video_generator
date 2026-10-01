import { Route, Routes } from 'react-router-dom'
import SelfiePage from './pages/SelfiePage'
import WelcomePage from './pages/WelcomePage'

function App() {
  return (
    <Routes>
      <Route path="/" element={<WelcomePage />} />
      <Route path="/selfie" element={<SelfiePage />} />
    </Routes>
  )
}

export default App
