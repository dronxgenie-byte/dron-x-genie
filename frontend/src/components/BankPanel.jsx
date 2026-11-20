import { useState, useEffect } from 'react'
import { getFamily, createTransaction, getTreasury } from '../api'

export default function BankPanel({ onClose }) {
  const [family, setFamily] = useState([])
  const [treasury, setTreasury] = useState(0)
  const [newTx, setNewTx] = useState({ user_id: '', amount: '', type: 'earn', description: '', category: '' })
  const [msg, setMsg] = useState('')

  useEffect(() => {
    loadData()
  }, [])

  async function loadData() {
    try {
      const [famResp, treasResp] = await Promise.all([getFamily(), getTreasury()])
      setFamily(famResp.data)
      setTreasury(treasResp.data.total_balance)
    } catch (err) {
      console.error('Ошибка загрузки банка:', err)
      setMsg('Ошибка загрузки данных банка')
    }
  }

  async function addTransaction(e) {
    e.preventDefault()
    try {
      const res = await createTransaction({
        user_id: parseInt(newTx.user_id),
        amount: parseFloat(newTx.amount),
        type: newTx.type,
        description: newTx.description,
        category: newTx.category,
      })
      setMsg('Транзакция добавлена')
      setNewTx({ user_id: '', amount: '', type: 'earn', description: '', category: '' })
      loadData()
    } catch (err) {
      console.error('Ошибка транзакции:', err)
      setMsg('Ошибка транзакции')
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/90 backdrop-blur-sm">
      <div
        className="absolute inset-0 bg-black/80 backdrop-blur"
        onClick={onClose}
      />
      <div className="relative w-full max-w-lg p-6 bg-gray-900 border border-gray-700 rounded-xl shadow-2xl max-h-[80vh] overflow-y-auto">
        <div className="flex justify-between items-center mb-6">
          <h2 className="text-xl font-bold text-blue-300">🏦 Банк Анисов</h2>
          <button onClick={onClose} className="text-gray-400 hover:text-white">✕</button>
        </div>

        <div className="mb-6 p-4 bg-gray-800/50 border border-gray-700 rounded-lg">
          <div className="flex justify-between text-sm mb-1">
            <span className="text-gray-400">Общий бюджет корабля:</span>
            <span className="font-bold text-yellow-400">{treasury.toFixed(0)} анисов</span>
          </div>
        </div>

        <div className="mb-6">
          <h3 className="text-sm font-bold text-gray-300 mb-3 uppercase tracking-wider">Члены экипажа</h3>
          <div className="space-y-2">
            {family.map((m) => (
              <div key={m.id} className="flex justify-between items-center p-2 bg-gray-800/50 rounded border border-gray-700/50">
                <div>
                  <div className="flex items-center gap-2">
                    <span className={`font-bold ${m.role === 'Captain' ? 'text-blue-300' : 'text-white'}`}>
                      {m.name}
                    </span>
                    {m.role === 'Captain' && (
                      <span className="text-xs bg-blue-900/30 text-blue-300 px-2 py-0.5 rounded border border-blue-500/30">
                        КАПИТАН
                      </span>
                    )}
                  </div>
                  <div className="text-xs text-gray-500">{m.role}</div>
                </div>
                <span className="font-mono text-lg">{m.balance.toFixed(0)} ан.</span>
              </div>
            ))}
          </div>
        </div>

        <form onSubmit={addTransaction} className="space-y-3">
          <h3 className="text-sm font-bold text-gray-300 mb-3 uppercase tracking-wider">Новая транзакция</h3>
          <div className="grid grid-cols-2 gap-3">
            <select
              value={newTx.user_id}
              onChange={(e) => setNewTx({ ...newTx, user_id: e.target.value })}
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="">Пользователь</option>
              {family.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.name}
                </option>
              ))}
            </select>
            <input
              type="number"
              value={newTx.amount}
              onChange={(e) => setNewTx({ ...newTx, amount: e.target.value })}
              placeholder="Сумма"
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <div className="grid grid-cols-3 gap-2">
            <select
              value={newTx.type}
              onChange={(e) => setNewTx({ ...newTx, type: e.target.value })}
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
            >
              <option value="earn">Доход</option>
              <option value="spend">Расход</option>
              <option value="transfer">Перевод</option>
              <option value="deposit">Вклад</option>
            </select>
            <input
              type="text"
              value={newTx.description}
              onChange={(e) => setNewTx({ ...newTx, description: e.target.value })}
              placeholder="Описание"
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
            />
            <input
              type="text"
              value={newTx.category}
              onChange={(e) => setNewTx({ ...newTx, category: e.target.value })}
              placeholder="Категория"
              className="bg-gray-800 border border-gray-600 rounded px-2 py-1 text-sm text-white focus:outline-none focus:border-blue-500"
            />
          </div>
          <button
            type="submit"
            className="w-full bg-blue-600 hover:bg-blue-500 text-white py-2 rounded font-bold transition"
          >
            Добавить
          </button>
        </form>

        {msg && (
          <div className="mt-3 p-2 bg-green-900/20 text-green-400 rounded text-sm border border-green-500/30">
            {msg}
          </div>
        )}
      </div>
    </div>
  )
}
