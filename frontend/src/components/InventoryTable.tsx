export function InventoryTable({ items }: { items: any[] }) {
  if (!items || items.length === 0) {
    return <p className="text-sm text-gray-400">無資料</p>
  }

  return (
    <div className="overflow-x-auto">
      <table className="w-full text-sm">
        <thead>
          <tr className="border-b border-gray-200">
            <th className="text-left py-2 px-3 text-gray-500 font-medium">料號</th>
            <th className="text-left py-2 px-3 text-gray-500 font-medium">品名</th>
            <th className="text-right py-2 px-3 text-gray-500 font-medium">數量</th>
            <th className="text-left py-2 px-3 text-gray-500 font-medium">單位</th>
            <th className="text-left py-2 px-3 text-gray-500 font-medium">儲位</th>
          </tr>
        </thead>
        <tbody>
          {items.map((item, i) => (
            <tr key={i} className="border-b border-gray-50 hover:bg-gray-50">
              <td className="py-2 px-3 font-mono text-xs">{item.part_no}</td>
              <td className="py-2 px-3">{item.name}</td>
              <td className="py-2 px-3 text-right font-medium">{item.quantity?.toLocaleString()}</td>
              <td className="py-2 px-3">{item.unit}</td>
              <td className="py-2 px-3 text-gray-500">{item.location || '-'}</td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}
