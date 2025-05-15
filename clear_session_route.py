@app.route('/clear_session', methods=['POST'])
def clear_session():
    """Limpa a sessão do usuário quando ele sai da página de resultados"""
    try:
        # Mantém apenas informações do usuário, limpa o resto
        user_info = session.get('user_info', None)
        session.clear()
        
        # Restaura informações do usuário se existirem
        if user_info:
            session['user_info'] = user_info
            
        logger.info("Sessão limpa com sucesso")
        return jsonify({'success': True, 'message': 'Sessão limpa com sucesso'})
    except Exception as e:
        logger.error(f"Erro ao limpar sessão: {str(e)}")
        return jsonify({'success': False, 'message': f'Erro: {str(e)}'}), 500
