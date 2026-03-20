import re

with open('src/views/clinic/patient/index.vue', 'r', encoding='utf-8') as f:
    vue_code = f.read()

with open('sichuan.txt', 'r', encoding='utf-8') as f:
    sichuan_options = f.read()

# 1. Replace regionOptions
vue_code = re.sub(
    r'regionOptions:\s*\[.*?\]\s*,\s*// 表单参数',
    f'regionOptions: {sichuan_options.strip()},\n      // 表单参数',
    vue_code,
    flags=re.DOTALL
)

# 2. Replace Allergy form item
vue_code = re.sub(
    r'<el-form-item label="过敏史" prop="allergies">\s*<el-select v-model="dynamicForm\.allergies" multiple filterable allow-create default-first-option placeholder="请选择或输入过敏史（回车确认）" style="width: 100%;">\s*</el-select>\s*</el-form-item>',
    '''<el-form-item label="过敏史" prop="allergies">
          <el-input v-model="dynamicForm.allergies" placeholder="请输入患者过敏史（如没有请留空）" />
        </el-form-item>''',
    vue_code
)

# 3. Replace Allergy table display
vue_code = re.sub(
    r'<template v-if="scope\.row\.dynamicProfile\.allergies && scope\.row\.dynamicProfile\.allergies\.length > 0">\s*<el-tag\s*v-for="\(allergy, index\) in scope\.row\.dynamicProfile\.allergies"\s*:key="\'allergy_\'\+index"\s*type="danger"\s*size="small"\s*style="margin.*?">\s*🚫 \{\{ allergy \}\}\s*</el-tag>\s*</template>',
    '''<div v-if="scope.row.dynamicProfile.allergies" style="margin-bottom: 5px; font-size: 13px; color: #F56C6C; white-space: pre-wrap;">
              <strong>过敏史：</strong>{{ scope.row.dynamicProfile.allergies }}
            </div>''',
    vue_code,
    flags=re.DOTALL
)

# 4. Replace allergies array to string
vue_code = vue_code.replace("allergies: []", "allergies: ''")

# 5. Fix handleUpdate fallback
vue_code = vue_code.replace("profile.allergies || []", "profile.allergies || ''")

# 6. Add Phone Rules
if 'pattern: /^1[3-9]' not in vue_code:
    vue_code = re.sub(
        r'(patientName:\s*\[\s*\{\s*required:\s*true.*?\}[\s\n]*\],)',
        r'\1\n        phone: [\n          { pattern: /^1[3-9]\\d{9}$/, message: "请输入正确的11位手机号码", trigger: "blur" }\n        ],',
        vue_code
    )

with open('src/views/clinic/patient/index.vue', 'w', encoding='utf-8') as f:
    f.write(vue_code)

print("Vue file successfully patched!")
