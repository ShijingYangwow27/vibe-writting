import { useEffect, useState } from 'react'
import { useParams, Link } from 'react-router-dom'
import { ArrowLeft, Plus, Trash2, Eye, EyeOff, Clock, Users, Search, X, ChevronDown, ChevronUp } from 'lucide-react'
import { storyApi } from '../api/client'
import { useToast } from '../components/Toast'

const TABS = [
  { id: 'foreshadowings', label: '伏笔', icon: Eye },
  { id: 'timeline', label: '时间线', icon: Clock },
  { id: 'characters', label: '角色', icon: Users },
]

export default function StoryElements() {
  const { id } = useParams()
  const { toast } = useToast()
  const [activeTab, setActiveTab] = useState('foreshadowings')
  const [foreshadowings, setForeshadowings] = useState([])
  const [timeline, setTimeline] = useState([])
  const [characters, setCharacters] = useState([])
  const [showForm, setShowForm] = useState(false)
  const [editingItem, setEditingItem] = useState(null)
  const [search, setSearch] = useState('')

  // 表单状态
  const [form, setForm] = useState({})
  const [expandedFs, setExpandedFs] = useState(null)

  useEffect(() => { loadAll() }, [id])

  const loadAll = async () => {
    try {
      const [fs, tl, ch] = await Promise.all([
        storyApi.listForeshadowings(id),
        storyApi.listTimeline(id),
        storyApi.listCharacters(id),
      ])
      setForeshadowings(fs.data)
      setTimeline(tl.data)
      setCharacters(ch.data)
    } catch (err) {
      toast.error('加载失败：' + err.message)
    }
  }

  // ── 伏笔操作 ──
  const handleSaveForeshadowing = async () => {
    try {
      if (editingItem) {
        await storyApi.updateForeshadowing(id, editingItem.id, form)
        toast.success('伏笔已更新')
      } else {
        await storyApi.createForeshadowing(id, form)
        toast.success('伏笔已创建')
      }
      setShowForm(false)
      setEditingItem(null)
      setForm({})
      loadAll()
    } catch (err) {
      toast.error('保存失败：' + err.message)
    }
  }

  const handleDeleteForeshadowing = async (fs) => {
    if (!confirm(`确定删除伏笔「${fs.name}」？`)) return
    try {
      await storyApi.deleteForeshadowing(id, fs.id)
      toast.success('伏笔已删除')
      loadAll()
    } catch (err) {
      toast.error('删除失败：' + err.message)
    }
  }

  const handleResolveForeshadowing = async (fs) => {
    const newStatus = fs.status === 'active' ? 'resolved' : 'active'
    const resolvedChapter = newStatus === 'resolved' ? prompt('在第几章回收？') : null
    try {
      await storyApi.updateForeshadowing(id, fs.id, {
        status: newStatus,
        chapter_resolved: resolvedChapter ? parseInt(resolvedChapter) : null,
      })
      toast.success(newStatus === 'resolved' ? '伏笔已回收' : '伏笔已重新激活')
      loadAll()
    } catch (err) {
      toast.error('操作失败：' + err.message)
    }
  }

  // ── 时间线操作 ──
  const handleSaveTimeline = async () => {
    try {
      if (editingItem) {
        await storyApi.updateTimelineEvent(id, editingItem.id, form)
        toast.success('事件已更新')
      } else {
        await storyApi.createTimelineEvent(id, form)
        toast.success('事件已创建')
      }
      setShowForm(false)
      setEditingItem(null)
      setForm({})
      loadAll()
    } catch (err) {
      toast.error('保存失败：' + err.message)
    }
  }

  const handleDeleteTimeline = async (event) => {
    if (!confirm(`确定删除事件「${event.description}」？`)) return
    try {
      await storyApi.deleteTimelineEvent(id, event.id)
      toast.success('事件已删除')
      loadAll()
    } catch (err) {
      toast.error('删除失败：' + err.message)
    }
  }

  // ── 角色操作 ──
  const handleSaveCharacter = async () => {
    try {
      if (editingItem) {
        await storyApi.updateCharacter(id, editingItem.id, form)
        toast.success('角色已更新')
      } else {
        await storyApi.createCharacter(id, form)
        toast.success('角色已创建')
      }
      setShowForm(false)
      setEditingItem(null)
      setForm({})
      loadAll()
    } catch (err) {
      toast.error('保存失败：' + err.message)
    }
  }

  const handleDeleteCharacter = async (ch) => {
    if (!confirm(`确定删除角色「${ch.name}」？`)) return
    try {
      await storyApi.deleteCharacter(id, ch.id)
      toast.success('角色已删除')
      loadAll()
    } catch (err) {
      toast.error('删除失败：' + err.message)
    }
  }

  const openCreateForm = () => {
    setEditingItem(null)
    setForm(activeTab === 'foreshadowings' ? { name: '', foreshadow_type: '', chapter_planted: 0, notes: '' }
      : activeTab === 'timeline' ? { chapter_number: 0, event_time: '', description: '', event_type: 'plot' }
      : { name: '', role: 'supporting', profile_data: {} })
    setShowForm(true)
  }

  const openEditForm = (item) => {
    setEditingItem(item)
    setForm(activeTab === 'characters'
      ? { name: item.name, role: item.role, profile_data: item.profile_data || {} }
      : { ...item })
    setShowForm(true)
  }

  const filteredFs = foreshadowings.filter(fs => !search || fs.name.includes(search) || fs.notes?.includes(search))
  const filteredTl = timeline.filter(t => !search || t.description.includes(search))
  const filteredCh = characters.filter(c => !search || c.name.includes(search))

  return (
    <div className="max-w-5xl mx-auto">
      {/* 头部 */}
      <div className="flex items-center justify-between mb-6">
        <div className="flex items-center gap-3">
          <Link to={`/project/${id}`} className="text-gray-400 hover:text-gray-600 transition-colors">
            <ArrowLeft className="w-5 h-5" />
          </Link>
          <div>
            <h1 className="text-xl font-bold text-gray-800">故事元素</h1>
            <p className="text-xs text-gray-400">管理伏笔、时间线和角色</p>
          </div>
        </div>
        <button onClick={openCreateForm}
          className="flex items-center gap-1.5 px-4 py-2 bg-purple-600 text-white rounded-xl hover:bg-purple-700 text-sm font-medium transition-all btn-press">
          <Plus className="w-4 h-4" />
          新建
        </button>
      </div>

      {/* 标签页 */}
      <div className="flex gap-1 bg-gray-100 p-1 rounded-xl mb-6">
        {TABS.map(tab => (
          <button key={tab.id} onClick={() => { setActiveTab(tab.id); setSearch('') }}
            className={`flex-1 flex items-center justify-center gap-2 py-2.5 rounded-lg text-sm font-medium transition-all ${
              activeTab === tab.id
                ? 'bg-white text-purple-600 shadow-sm'
                : 'text-gray-500 hover:text-gray-700'
            }`}>
            <tab.icon className="w-4 h-4" />
            {tab.label}
            <span className="text-xs opacity-60">
              {tab.id === 'foreshadowings' ? foreshadowings.length :
               tab.id === 'timeline' ? timeline.length : characters.length}
            </span>
          </button>
        ))}
      </div>

      {/* 搜索 */}
      <div className="relative mb-4">
        <Search className="absolute left-3 top-1/2 -translate-y-1/2 w-4 h-4 text-gray-400" />
        <input value={search} onChange={(e) => setSearch(e.target.value)}
          placeholder={`搜索${activeTab === 'foreshadowings' ? '伏笔' : activeTab === 'timeline' ? '事件' : '角色'}...`}
          className="w-full pl-10 pr-4 py-2.5 bg-white border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none" />
      </div>

      {/* 内容区 */}
      <div className="space-y-3">
        {/* ── 伏笔列表 ── */}
        {activeTab === 'foreshadowings' && (
          filteredFs.length === 0 ? (
            <EmptyState icon="🔮" text="还没有伏笔" hint="点击上方「新建」添加" />
          ) : filteredFs.map(fs => (
            <div key={fs.id} className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
              <div className="flex items-start justify-between">
                <div className="flex-1">
                  <div className="flex items-center gap-2 mb-1">
                    <span className={`w-2 h-2 rounded-full ${fs.status === 'active' ? 'bg-amber-400' : 'bg-green-400'}`} />
                    <span className="text-sm font-medium text-gray-800">{fs.name}</span>
                    {fs.foreshadow_type && (
                      <span className="text-[10px] px-1.5 py-0.5 bg-gray-100 text-gray-500 rounded">{fs.foreshadow_type}</span>
                    )}
                  </div>
                  <div className="flex items-center gap-3 text-xs text-gray-400">
                    <span>第{fs.chapter_planted}章埋设</span>
                    {fs.chapter_resolved && <span>· 第{fs.chapter_resolved}章回收</span>}
                    <span>· {fs.status === 'active' ? '活跃' : '已回收'}</span>
                  </div>
                  {fs.notes && <p className="text-xs text-gray-500 mt-2 line-clamp-2">{fs.notes}</p>}
                </div>
                <div className="flex items-center gap-1 ml-2">
                  <button onClick={() => handleResolveForeshadowing(fs)}
                    className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors" title={fs.status === 'active' ? '标记回收' : '重新激活'}>
                    {fs.status === 'active' ? <EyeOff className="w-3.5 h-3.5 text-gray-400" /> : <Eye className="w-3.5 h-3.5 text-green-500" />}
                  </button>
                  <button onClick={() => openEditForm(fs)} className="p-1.5 rounded-lg hover:bg-gray-100 transition-colors text-xs text-gray-400">编辑</button>
                  <button onClick={() => handleDeleteForeshadowing(fs)} className="p-1.5 rounded-lg hover:bg-red-50 transition-colors">
                    <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
                  </button>
                </div>
              </div>
            </div>
          ))
        )}

        {/* ── 时间线列表 ── */}
        {activeTab === 'timeline' && (
          filteredTl.length === 0 ? (
            <EmptyState icon="📅" text="还没有事件" hint="点击上方「新建」添加" />
          ) : (
            <div className="relative pl-6">
              {/* 时间线竖线 */}
              <div className="absolute left-2.5 top-0 bottom-0 w-0.5 bg-gray-200" />
              {filteredTl.map((event, i) => (
                <div key={event.id} className="relative mb-4">
                  {/* 节点 */}
                  <div className={`absolute -left-3.5 top-3 w-3 h-3 rounded-full border-2 border-white ${
                    event.event_type === 'plot' ? 'bg-purple-500' :
                    event.event_type === 'relationship' ? 'bg-pink-500' :
                    event.event_type === 'character_change' ? 'bg-blue-500' : 'bg-gray-400'
                  }`} />
                  <div className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                    <div className="flex items-start justify-between">
                      <div>
                        <div className="flex items-center gap-2 mb-1">
                          <span className="text-xs font-bold text-purple-600 bg-purple-50 px-2 py-0.5 rounded">第{event.chapter_number}章</span>
                          {event.event_time && <span className="text-xs text-gray-400">{event.event_time}</span>}
                          <span className={`text-[10px] px-1.5 py-0.5 rounded ${
                            event.event_type === 'plot' ? 'bg-purple-50 text-purple-600' :
                            event.event_type === 'relationship' ? 'bg-pink-50 text-pink-600' :
                            'bg-blue-50 text-blue-600'
                          }`}>
                            {event.event_type === 'plot' ? '剧情' : event.event_type === 'relationship' ? '关系' : '角色变化'}
                          </span>
                        </div>
                        <p className="text-sm text-gray-700">{event.description}</p>
                      </div>
                      <div className="flex items-center gap-1 ml-2">
                        <button onClick={() => openEditForm(event)} className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-100">编辑</button>
                        <button onClick={() => handleDeleteTimeline(event)} className="p-1.5 rounded-lg hover:bg-red-50">
                          <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
                        </button>
                      </div>
                    </div>
                  </div>
                </div>
              ))}
            </div>
          )
        )}

        {/* ── 角色列表 ── */}
        {activeTab === 'characters' && (
          filteredCh.length === 0 ? (
            <EmptyState icon="👤" text="还没有角色" hint="点击上方「新建」添加" />
          ) : (
            <div className="grid grid-cols-1 md:grid-cols-2 gap-3">
              {filteredCh.map(ch => (
                <div key={ch.id} className="bg-white border border-gray-200 rounded-xl p-4 hover:shadow-sm transition-all">
                  <div className="flex items-start justify-between">
                    <div className="flex items-center gap-3">
                      <div className={`w-10 h-10 rounded-xl flex items-center justify-center text-sm font-bold ${
                        ch.role === 'protagonist' ? 'bg-purple-100 text-purple-600' :
                        ch.role === 'antagonist' ? 'bg-red-100 text-red-600' :
                        'bg-gray-100 text-gray-600'
                      }`}>
                        {ch.name?.[0] || '?'}
                      </div>
                      <div>
                        <p className="text-sm font-medium text-gray-800">{ch.name}</p>
                        <p className="text-xs text-gray-400">
                          {ch.role === 'protagonist' ? '主角' : ch.role === 'antagonist' ? '反派' : '配角'}
                        </p>
                      </div>
                    </div>
                    <div className="flex items-center gap-1">
                      <button onClick={() => openEditForm(ch)} className="text-xs text-gray-400 hover:text-gray-600 px-1.5 py-0.5 rounded hover:bg-gray-100">编辑</button>
                      <button onClick={() => handleDeleteCharacter(ch)} className="p-1.5 rounded-lg hover:bg-red-50">
                        <Trash2 className="w-3.5 h-3.5 text-gray-400 hover:text-red-500" />
                      </button>
                    </div>
                  </div>
                  {ch.profile_data && (
                    <div className="mt-3 space-y-1">
                      {ch.profile_data.性格核心 && (
                        <p className="text-xs text-gray-500"><span className="text-gray-400">性格：</span>{ch.profile_data.性格核心}</p>
                      )}
                      {ch.profile_data.核心价值观 && (
                        <p className="text-xs text-gray-500"><span className="text-gray-400">价值观：</span>{ch.profile_data.核心价值观}</p>
                      )}
                      {ch.profile_data.致命缺陷 && (
                        <p className="text-xs text-gray-500"><span className="text-gray-400">缺陷：</span>{ch.profile_data.致命缺陷}</p>
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )
        )}
      </div>

      {/* ── 表单弹窗 ── */}
      {showForm && (
        <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
          <div className="bg-white rounded-2xl w-full max-w-lg shadow-2xl overflow-hidden">
            <div className="px-6 py-4 border-b border-gray-100 flex items-center justify-between">
              <h2 className="text-lg font-bold text-gray-800">
                {editingItem ? '编辑' : '新建'}{
                  activeTab === 'foreshadowings' ? '伏笔' :
                  activeTab === 'timeline' ? '事件' : '角色'
                }
              </h2>
              <button onClick={() => { setShowForm(false); setEditingItem(null) }} className="text-gray-400 hover:text-gray-600">
                <X className="w-5 h-5" />
              </button>
            </div>
            <div className="px-6 py-5 space-y-4 max-h-[60vh] overflow-y-auto">
              {/* 伏笔表单 */}
              {activeTab === 'foreshadowings' && (
                <>
                  <Field label="伏笔名称" value={form.name || ''} onChange={v => setForm({ ...form, name: v })} placeholder="例如：古剑的秘密" />
                  <Field label="类型" value={form.foreshadow_type || ''} onChange={v => setForm({ ...form, foreshadow_type: v })} placeholder="例如：身世、阴谋、感情" />
                  <Field label="埋设章节" type="number" value={form.chapter_planted || 0} onChange={v => setForm({ ...form, chapter_planted: parseInt(v) || 0 })} />
                  <Field label="备注" textarea value={form.notes || ''} onChange={v => setForm({ ...form, notes: v })} placeholder="伏笔的详细说明..." />
                </>
              )}
              {/* 时间线表单 */}
              {activeTab === 'timeline' && (
                <>
                  <Field label="章节" type="number" value={form.chapter_number || 0} onChange={v => setForm({ ...form, chapter_number: parseInt(v) || 0 })} />
                  <Field label="时间" value={form.event_time || ''} onChange={v => setForm({ ...form, event_time: v })} placeholder="例如：三个月后、黄昏" />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">事件类型</label>
                    <select value={form.event_type || 'plot'} onChange={(e) => setForm({ ...form, event_type: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none">
                      <option value="plot">剧情</option>
                      <option value="relationship">关系</option>
                      <option value="character_change">角色变化</option>
                    </select>
                  </div>
                  <Field label="描述" textarea value={form.description || ''} onChange={v => setForm({ ...form, description: v })} placeholder="发生了什么..." />
                </>
              )}
              {/* 角色表单 */}
              {activeTab === 'characters' && (
                <>
                  <Field label="姓名" value={form.name || ''} onChange={v => setForm({ ...form, name: v })} placeholder="角色姓名" />
                  <div>
                    <label className="block text-sm font-medium text-gray-700 mb-1.5">角色类型</label>
                    <select value={form.role || 'supporting'} onChange={(e) => setForm({ ...form, role: e.target.value })}
                      className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 outline-none">
                      <option value="protagonist">主角</option>
                      <option value="antagonist">反派</option>
                      <option value="supporting">配角</option>
                    </select>
                  </div>
                  <Field label="性格核心" value={form.profile_data?.性格核心 || ''} onChange={v => setForm({ ...form, profile_data: { ...form.profile_data, 性格核心: v } })} placeholder="描述角色性格..." />
                  <Field label="核心价值观" value={form.profile_data?.核心价值观 || ''} onChange={v => setForm({ ...form, profile_data: { ...form.profile_data, 核心价值观: v } })} placeholder="角色最看重什么..." />
                  <Field label="致命缺陷" value={form.profile_data?.致命缺陷 || ''} onChange={v => setForm({ ...form, profile_data: { ...form.profile_data, 致命缺陷: v } })} placeholder="角色的弱点..." />
                  <Field label="内心渴望" value={form.profile_data?.内心渴望 || ''} onChange={v => setForm({ ...form, profile_data: { ...form.profile_data, 内心渴望: v } })} placeholder="角色真正想要什么..." />
                </>
              )}
            </div>
            <div className="px-6 py-4 border-t border-gray-100 flex gap-3">
              <button onClick={activeTab === 'foreshadowings' ? handleSaveForeshadowing : activeTab === 'timeline' ? handleSaveTimeline : handleSaveCharacter}
                className="flex-1 py-2.5 bg-purple-600 text-white rounded-xl hover:bg-purple-700 text-sm font-medium transition-all btn-press">
                保存
              </button>
              <button onClick={() => { setShowForm(false); setEditingItem(null) }}
                className="px-4 py-2.5 border border-gray-200 text-gray-600 rounded-xl hover:bg-gray-50 text-sm transition-colors">
                取消
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

// 通用字段组件
function Field({ label, value, onChange, placeholder, textarea, type = 'text' }) {
  const Comp = textarea ? 'textarea' : 'input'
  return (
    <div>
      <label className="block text-sm font-medium text-gray-700 mb-1.5">{label}</label>
      <Comp type={type} value={value} onChange={(e) => onChange(e.target.value)}
        className="w-full px-4 py-2.5 border border-gray-200 rounded-xl text-sm focus:ring-2 focus:ring-purple-500 focus:border-transparent outline-none transition-all resize-none"
        placeholder={placeholder} rows={textarea ? 3 : undefined} />
    </div>
  )
}

// 空状态
function EmptyState({ icon, text, hint }) {
  return (
    <div className="text-center py-16">
      <div className="text-4xl mb-3">{icon}</div>
      <p className="text-sm font-medium text-gray-600 mb-1">{text}</p>
      <p className="text-xs text-gray-400">{hint}</p>
    </div>
  )
}
