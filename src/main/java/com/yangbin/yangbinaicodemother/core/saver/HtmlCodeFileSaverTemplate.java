package com.yangbin.yangbinaicodemother.core.saver;

import cn.hutool.core.util.StrUtil;
import com.yangbin.yangbinaicodemother.ai.model.HtmlCodeResult;
import com.yangbin.yangbinaicodemother.exception.BusinessException;
import com.yangbin.yangbinaicodemother.exception.ErrorCode;
import com.yangbin.yangbinaicodemother.model.enums.CodeGenTypeEnum;

/**
 * HTML代码文件保存器
 *
 * Upstream attribution: see NOTICE.md.
 */
public class HtmlCodeFileSaverTemplate extends CodeFileSaverTemplate<HtmlCodeResult> {

    @Override
    protected CodeGenTypeEnum getCodeType() {
        return CodeGenTypeEnum.HTML;
    }

    @Override
    protected void saveFiles(HtmlCodeResult result, String baseDirPath) {
        writeToFile(baseDirPath, "index.html", result.getHtmlCode());
    }

    @Override
    protected void validateInput(HtmlCodeResult result) {
        super.validateInput(result);
        // HTML 代码不能为空
        if (StrUtil.isBlank(result.getHtmlCode())) {
            throw new BusinessException(ErrorCode.SYSTEM_ERROR, "HTML 代码不能为空");
        }
    }
}
