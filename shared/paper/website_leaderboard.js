const leaderboardData = [
  {rank: 1, model: "GPT-5.4", provider: "OpenAI", oracle: 0.735, restricted: 0.691, noPlan: 0.796, noVerify: 0.746, full: 0.858, uplift: 0.122, tni: 0.771, teamHelps: 0.71},
  {rank: 2, model: "Claude Haiku 4.5", provider: "Anthropic", oracle: 0.681, restricted: 0.710, noPlan: 0.710, noVerify: 0.764, full: 0.849, uplift: 0.168, tni: 0.583, teamHelps: 0.79},
  {rank: 3, model: "Gemini 3.1 Lite", provider: "Google", oracle: 0.673, restricted: 0.652, noPlan: 0.656, noVerify: 0.716, full: 0.770, uplift: 0.097, tni: 0.949, teamHelps: 0.57},
  {rank: 4, model: "GPT-5 Mini", provider: "OpenAI", oracle: 0.711, restricted: 0.590, noPlan: 0.671, noVerify: 0.735, full: 0.756, uplift: 0.044, tni: 1.182, teamHelps: 0.57},
  {rank: 5, model: "Gemini 3 Flash", provider: "Google", oracle: 0.699, restricted: 0.696, noPlan: 0.715, noVerify: 0.739, full: 0.754, uplift: 0.055, tni: 0.534, teamHelps: 0.50},
  {rank: 6, model: "GPT-5 Nano", provider: "OpenAI", oracle: 0.689, restricted: 0.428, noPlan: 0.635, noVerify: 0.558, full: 0.678, uplift: -0.011, tni: 0.841, teamHelps: 0.79},
  {rank: 7, model: "Claude Sonnet 4.6", provider: "Anthropic", oracle: 0.766, restricted: 0.697, noPlan: 0.776, noVerify: 0.726, full: 0.669, uplift: -0.097, tni: 0.273, teamHelps: 0.36},
  {rank: 8, model: "GPT-5.3 Chat", provider: "OpenAI", oracle: 0.611, restricted: 0.503, noPlan: 0.504, noVerify: 0.686, full: 0.667, uplift: 0.056, tni: 0.892, teamHelps: 0.61},
  {rank: 9, model: "Qwen3.5-35B-A3B", provider: "Alibaba", oracle: 0.692, restricted: 0.695, noPlan: 0.350, noVerify: 0.410, full: 0.597, uplift: -0.095, tni: 0.015, teamHelps: 0.32},
  {rank: 10, model: "Qwen3.5-4B", provider: "Alibaba", oracle: 0.506, restricted: 0.476, noPlan: 0.588, noVerify: 0.562, full: 0.512, uplift: 0.006, tni: 0.595, teamHelps: 0.32},
  {rank: 11, model: "Qwen3.5-9B", provider: "Alibaba", oracle: 0.628, restricted: 0.569, noPlan: 0.589, noVerify: 0.574, full: 0.500, uplift: -0.128, tni: 0.624, teamHelps: 0.36},
  {rank: 12, model: "Qwen3.5-2B", provider: "Alibaba", oracle: 0.396, restricted: 0.318, noPlan: 0.310, noVerify: 0.456, full: 0.351, uplift: -0.045, tni: 0.125, teamHelps: 0.32},
  {rank: 13, model: "Qwen3.5-0.8B", provider: "Alibaba", oracle: 0.397, restricted: 0.315, noPlan: 0.320, noVerify: 0.411, full: 0.343, uplift: -0.054, tni: 0.194, teamHelps: 0.14},
  {rank: 14, model: "Qwen2.5-Coder-32B", provider: "Alibaba", oracle: 0.350, restricted: 0.336, noPlan: 0.338, noVerify: 0.425, full: 0.335, uplift: -0.015, tni: 0.729, teamHelps: 0.04},
  {rank: 15, model: "Qwen3-14B", provider: "Alibaba", oracle: 0.295, restricted: 0.308, noPlan: 0.313, noVerify: 0.347, full: 0.328, uplift: 0.033, tni: 0.261, teamHelps: 0.39},
  {rank: 16, model: "GPT-OSS-20B", provider: "OpenAI", oracle: 0.448, restricted: 0.369, noPlan: 0.385, noVerify: 0.418, full: 0.303, uplift: -0.145, tni: 0.856, teamHelps: 0.21},
  {rank: 17, model: "Qwen3-8B", provider: "Alibaba", oracle: 0.320, restricted: 0.293, noPlan: 0.322, noVerify: 0.353, full: 0.295, uplift: -0.024, tni: 0.340, teamHelps: 0.32},
  {rank: 18, model: "Qwen3-4B", provider: "Alibaba", oracle: 0.260, restricted: 0.287, noPlan: 0.284, noVerify: 0.288, full: 0.181, uplift: -0.079, tni: 0.437, teamHelps: 0.04},
  {rank: 19, model: "DeepSeek-R1-Distill-32B", provider: "DeepSeek", oracle: 0.326, restricted: 0.316, noPlan: 0.316, noVerify: 0.263, full: 0.127, uplift: -0.199, tni: 0.000, teamHelps: 0.00},
  {rank: 20, model: "Qwen3.5-27B", provider: "Alibaba", oracle: 0.243, restricted: 0.149, noPlan: 0.190, noVerify: 0.065, full: 0.064, uplift: -0.179, tni: -0.162, teamHelps: 0.07},
  {rank: 21, model: "Qwen3-Coder-30B-A3B", provider: "Alibaba", oracle: 0.243, restricted: 0.251, noPlan: 0.142, noVerify: 0.095, full: 0.030, uplift: -0.213, tni: 0.531, teamHelps: 0.04},
  {rank: 22, model: "CodeGemma 7B", provider: "Google", oracle: 0.000, restricted: 0.000, noPlan: 0.000, noVerify: 0.000, full: 0.000, uplift: 0.000, tni: 0.000, teamHelps: 0.00},
  {rank: 23, model: "Devstral-24B", provider: "Mistral", oracle: 0.000, restricted: 0.000, noPlan: 0.000, noVerify: 0.000, full: 0.000, uplift: 0.000, tni: 0.000, teamHelps: 0.00},
  {rank: 24, model: "Gemma 3 27B", provider: "Google", oracle: 0.152, restricted: 0.214, noPlan: 0.287, noVerify: 0.000, full: 0.000, uplift: -0.152, tni: 0.667, teamHelps: 0.00},
];

const ablationChartLabels = [
  "GPT-5.4",
  "Claude Haiku 4.5",
  "Gemini 3.1 Lite",
  "GPT-5 Mini",
  "Gemini 3 Flash",
  "GPT-5 Nano",
  "Claude Sonnet 4.6",
  "GPT-5.3 Chat",
  "Qwen3.5-35B-A3B",
  "Qwen3.5-4B",
  "Qwen3.5-9B",
  "Qwen3.5-2B",
  "Qwen3.5-0.8B",
  "Qwen2.5-Coder-32B",
  "Qwen3-14B",
  "GPT-OSS-20B",
  "Qwen3-8B",
  "Qwen3-4B",
  "DeepSeek-R1-Distill-32B",
  "Qwen3.5-27B",
  "Qwen3-Coder-30B-A3B",
  "CodeGemma 7B",
  "Devstral-24B",
  "Gemma 3 27B",
];
const ablationOracleData = [0.735, 0.681, 0.673, 0.711, 0.699, 0.689, 0.766, 0.611, 0.692, 0.506, 0.628, 0.396, 0.397, 0.350, 0.295, 0.448, 0.320, 0.260, 0.326, 0.243, 0.243, 0.000, 0.000, 0.152];
const ablationRestrictedData = [0.691, 0.710, 0.652, 0.590, 0.696, 0.428, 0.697, 0.503, 0.695, 0.476, 0.569, 0.318, 0.315, 0.336, 0.308, 0.369, 0.293, 0.287, 0.316, 0.149, 0.251, 0.000, 0.000, 0.214];
const ablationNoPlannerData = [0.796, 0.710, 0.656, 0.671, 0.715, 0.635, 0.776, 0.504, 0.350, 0.588, 0.589, 0.310, 0.320, 0.338, 0.313, 0.385, 0.322, 0.284, 0.316, 0.190, 0.142, 0.000, 0.000, 0.287];
const ablationNoEvaluatorData = [0.746, 0.764, 0.716, 0.735, 0.739, 0.558, 0.726, 0.686, 0.410, 0.562, 0.574, 0.456, 0.411, 0.425, 0.347, 0.418, 0.353, 0.288, 0.263, 0.065, 0.095, 0.000, 0.000, 0.000];
const ablationFullData = [0.858, 0.849, 0.770, 0.756, 0.754, 0.678, 0.669, 0.667, 0.597, 0.512, 0.500, 0.351, 0.343, 0.335, 0.328, 0.303, 0.295, 0.181, 0.127, 0.064, 0.030, 0.000, 0.000, 0.000];

const upliftData = [0.122, 0.168, 0.097, 0.044, 0.055, -0.011, -0.097, 0.056, -0.095, 0.006, -0.128, -0.045, -0.054, -0.015, 0.033, -0.145, -0.024, -0.079, -0.199, -0.179, -0.213, 0.000, 0.000, -0.152];
