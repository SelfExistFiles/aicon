import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import chaptersService from '@/services/chapters'
import apiKeysService from '@/services/apiKeys'
import api from '@/services/api'

export function useDirectorEngine(projectId) {
  // 状态管理
  const chapters = ref([])
  const apiKeys = ref([])
  const sentences = ref([])
  const selectedChapterId = ref('')
  const loading = ref(false)
  const loadingStates = ref({})

  // 对话框状态
  const generatePromptsVisible = ref(false)
  const regeneratePromptsVisible = ref(false)
  const batchGenerateImagesVisible = ref(false)
  const selectedSentenceIds = ref([])

  // 加载已确认的章节
  const loadChapters = async () => {
    try {
      const res = await chaptersService.getConfirmedChapters(projectId)
      chapters.value = res.chapters || []
    } catch (error) {
      console.error('加载章节失败', error)
    }
  }

  // 加载API Keys
  const loadApiKeys = async () => {
    const res = await apiKeysService.getAPIKeys()
    apiKeys.value = res.api_keys || []
  }

  // 加载句子
  const loadSentences = async () => {
    if (!selectedChapterId.value) return
    
    loading.value = true
    try {
      const response = await api.get(`/chapters/${selectedChapterId.value}/sentences`)
      sentences.value = response.sentences || []
      
      // 初始化加载状态
      const initialLoadingStates = {}
      sentences.value.forEach(sentence => {
        initialLoadingStates[sentence.id] = {
          generatingPrompt: false,
          generatingAudio: false,
          generatingImage: false
        }
      })
      loadingStates.value = initialLoadingStates
    } catch (error) {
      console.error('加载句子失败', error)
      ElMessage.error('加载句子失败')
    } finally {
      loading.value = false
    }
  }

  // 更新句子的加载状态
  const updateSentenceLoadingState = (sentenceId, newState) => {
    loadingStates.value = {
      ...loadingStates.value,
      [sentenceId]: {
        ...loadingStates.value[sentenceId],
        ...newState
      }
    }
  }

  // 处理提示词操作（查看/编辑）
  const handlePromptAction = async (action, sentence) => {
    try {
      // 从接口获取最新的句子数据
      const response = await api.get(`/sentences/${sentence.id}`)
      const latestSentence = response
      
      return {
        action,
        sentence: latestSentence
      }
    } catch (error) {
      console.error('获取句子数据失败', error)
      ElMessage.error('获取句子数据失败，请稍后重试')
      return null
    }
  }

  // 初始化
  onMounted(() => {
    loadChapters()
    loadApiKeys()
  })

  return {
    // 状态
    chapters,
    apiKeys,
    sentences,
    selectedChapterId,
    loading,
    loadingStates,
    
    // 对话框状态
    generatePromptsVisible,
    regeneratePromptsVisible,
    batchGenerateImagesVisible,
    selectedSentenceIds,
    
    // 方法
    loadChapters,
    loadSentences,
    updateSentenceLoadingState,
    handlePromptAction
  }
}