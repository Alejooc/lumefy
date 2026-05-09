import { CommonModule } from '@angular/common';
import { AfterViewInit, Component, ElementRef, EventEmitter, Input, OnChanges, Output, SimpleChanges, ViewChild } from '@angular/core';

type EditorCommand =
  | 'bold'
  | 'italic'
  | 'underline'
  | 'insertUnorderedList'
  | 'insertOrderedList'
  | 'formatBlock'
  | 'removeFormat';

@Component({
  selector: 'app-rich-text-editor',
  standalone: true,
  imports: [CommonModule],
  templateUrl: './rich-text-editor.component.html',
  styleUrls: ['./rich-text-editor.component.scss']
})
export class RichTextEditorComponent implements AfterViewInit, OnChanges {
  @Input() value = '';
  @Input() placeholder = 'Escribe aqui...';
  @Input() minHeight = 220;
  @Output() valueChange = new EventEmitter<string>();

  @ViewChild('editor') editorRef?: ElementRef<HTMLDivElement>;

  private lastRenderedValue = '';

  ngAfterViewInit(): void {
    this.renderValue(this.value);
  }

  ngOnChanges(changes: SimpleChanges): void {
    if ('value' in changes && !changes['value'].firstChange) {
      this.renderValue(this.value);
    }
  }

  exec(command: EditorCommand, commandValue?: string): void {
    this.focusEditor();
    document.execCommand(command, false, commandValue);
    this.emitValue();
  }

  insertLink(): void {
    const url = window.prompt('URL del enlace');
    if (!url) {
      return;
    }

    this.focusEditor();
    document.execCommand('createLink', false, url.trim());
    this.emitValue();
  }

  insertTable(): void {
    this.focusEditor();
    const tableHtml = `
      <table>
        <thead>
          <tr>
            <th>Columna 1</th>
            <th>Columna 2</th>
          </tr>
        </thead>
        <tbody>
          <tr>
            <td>Dato 1</td>
            <td>Dato 2</td>
          </tr>
        </tbody>
      </table>
      <p></p>
    `;
    document.execCommand('insertHTML', false, tableHtml);
    this.emitValue();
  }

  onInput(): void {
    this.emitValue();
  }

  onBlur(): void {
    const sanitized = this.sanitizeHtml(this.editorRef?.nativeElement.innerHTML || '');
    this.renderValue(sanitized, true);
    this.valueChange.emit(sanitized);
  }

  onPaste(event: ClipboardEvent): void {
    event.preventDefault();
    const text = event.clipboardData?.getData('text/plain') || '';
    this.focusEditor();
    document.execCommand('insertText', false, text);
    this.emitValue();
  }

  private emitValue(): void {
    const html = this.editorRef?.nativeElement.innerHTML || '';
    this.lastRenderedValue = html;
    this.valueChange.emit(html);
  }

  private renderValue(value: string, force = false): void {
    const editor = this.editorRef?.nativeElement;
    if (!editor) {
      return;
    }

    const nextValue = this.sanitizeHtml(value || '');
    if (!force && nextValue === this.lastRenderedValue) {
      return;
    }

    editor.innerHTML = nextValue;
    this.lastRenderedValue = nextValue;
  }

  private focusEditor(): void {
    this.editorRef?.nativeElement.focus();
  }

  private sanitizeHtml(value: string): string {
    if (!value) {
      return '';
    }

    const parser = new DOMParser();
    const doc = parser.parseFromString(value, 'text/html');

    doc.querySelectorAll('script,style,iframe,object,embed').forEach((node) => node.remove());

    doc.querySelectorAll('*').forEach((element) => {
      Array.from(element.attributes).forEach((attribute) => {
        const name = attribute.name.toLowerCase();
        const currentValue = attribute.value;
        if (name.startsWith('on')) {
          element.removeAttribute(attribute.name);
        }
        if ((name === 'href' || name === 'src') && /^javascript:/i.test(currentValue)) {
          element.removeAttribute(attribute.name);
        }
      });
    });

    return doc.body.innerHTML;
  }
}
